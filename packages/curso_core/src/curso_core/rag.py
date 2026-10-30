"""Piezas de RAG: trocear documentos e indexarlos para buscar por similitud.

El índice vive en memoria con numpy, para que se vea cómo funciona, o en PostgreSQL con
pgvector. Crece en el módulo 3: troceado, índice vectorial, búsqueda léxica, híbrida y
reranking.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from curso_core.client import ClienteLLM

SECCION = re.compile(r"^## ", re.M)
PALABRA = re.compile(r"\w+")
# Palabras tan frecuentes en español que no ayudan a distinguir un fragmento de otro.
_VACIAS = """
a al como con cual cuales cuando cuanto de del donde el en es esta este hay la las le lo los
mas me no o para pero por que quien se si sin son su sus un una y ya
"""
VACIAS = frozenset(_VACIAS.split())


class Fragmento(BaseModel):
    """Un trozo de un documento, la unidad que se indexa y se recupera."""

    id: str
    doc: str
    titulo: str
    texto: str

    def para_indexar(self) -> str:
        """El texto que se convierte en embedding: con su título, que da contexto."""
        return f"{self.titulo}\n\n{self.texto}"


class Resultado(BaseModel):
    fragmento: Fragmento
    puntuacion: float


def leer_documentos(carpeta: Path) -> dict[str, str]:
    """`{nombre: texto}` de todos los Markdown de una carpeta, en orden alfabético."""
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(carpeta.glob("*.md"))}


def _titulo(texto: str) -> tuple[str, str]:
    """Separa la primera línea `# Título` del resto."""
    primera, _, resto = texto.partition("\n")
    return primera.removeprefix("# ").strip(), resto


def trocear_por_secciones(doc: str, texto: str) -> list[Fragmento]:
    """Un fragmento por sección `##`; lo anterior a la primera sección va aparte."""
    titulo, cuerpo = _titulo(texto)
    partes = SECCION.split(cuerpo)
    fragmentos = []
    for i, parte in enumerate(partes):
        parte = parte.strip()
        if not parte:
            continue
        if i == 0:
            seccion, contenido = titulo, parte
        else:
            encabezado, _, contenido = parte.partition("\n")
            seccion, contenido = f"{titulo} > {encabezado.strip()}", contenido.strip()
        fragmentos.append(
            Fragmento(id=f"{doc}#{i}", doc=doc, titulo=seccion, texto=contenido or seccion)
        )
    return fragmentos


def trocear_fijo(doc: str, texto: str, palabras: int, solape: int = 0) -> list[Fragmento]:
    """Fragmentos de `palabras` palabras, solapados `solape` palabras, sin mirar la estructura."""
    if not 0 <= solape < palabras:
        raise ValueError("El solape tiene que ser menor que el tamaño del fragmento")
    titulo, cuerpo = _titulo(texto)
    tokens = cuerpo.split()
    paso = palabras - solape
    return [
        Fragmento(
            id=f"{doc}@{inicio}",
            doc=doc,
            titulo=titulo,
            texto=" ".join(tokens[inicio : inicio + palabras]),
        )
        for inicio in range(0, max(1, len(tokens) - solape), paso)
    ]


class IndiceVectorial:
    """Índice en memoria: guarda los embeddings normalizados y busca por coseno."""

    def __init__(
        self,
        cliente: ClienteLLM,
        rol: str = "embeddings",
        lote: int = 32,
        prefijo_documento: str = "",
        prefijo_consulta: str = "",
    ):
        """Algunos modelos de embeddings piden prefijos de tarea (por ejemplo,
        `search_document: ` y `search_query: `): consulta la ficha del tuyo."""
        self.cliente = cliente
        self.rol = rol
        self.lote = lote
        self.prefijo_documento = prefijo_documento
        self.prefijo_consulta = prefijo_consulta
        self.fragmentos: list[Fragmento] = []
        self._matriz = np.zeros((0, 0), dtype=np.float32)

    @property
    def dimensiones(self) -> int:
        """Longitud de los vectores del índice (0 si está vacío)."""
        return self._matriz.shape[1] if self.fragmentos else 0

    def _vectores(self, textos: Sequence[str]) -> np.ndarray:
        vectores = []
        for i in range(0, len(textos), self.lote):
            vectores += self.cliente.embeber(list(textos[i : i + self.lote]), rol=self.rol).vectores
        matriz = np.array(vectores, dtype=np.float32)
        # Normalizados, el producto escalar es directamente la similitud del coseno.
        return matriz / np.linalg.norm(matriz, axis=1, keepdims=True)

    def añadir(self, fragmentos: Sequence[Fragmento]) -> None:
        nuevos = self._vectores([self.prefijo_documento + f.para_indexar() for f in fragmentos])
        self._matriz = nuevos if not self.fragmentos else np.vstack([self._matriz, nuevos])
        self.fragmentos += list(fragmentos)

    def buscar(self, consulta: str, k: int = 3) -> list[Resultado]:
        vector = self._vectores([self.prefijo_consulta + consulta])[0]
        puntuaciones = self._matriz @ vector
        mejores = np.argsort(-puntuaciones)[:k]
        return [
            Resultado(fragmento=self.fragmentos[i], puntuacion=float(puntuaciones[i]))
            for i in mejores
        ]


class IndicePgvector(IndiceVectorial):
    """El mismo índice, guardado en PostgreSQL con la extensión pgvector.

    Mismos métodos que `IndiceVectorial`; cambia dónde viven los vectores. La búsqueda la
    hace la base de datos con el operador de distancia del coseno (`<=>`) y un índice HNSW.
    Necesita un PostgreSQL con pgvector (en el repo: `docker compose up -d`).
    """

    def __init__(
        self,
        cliente: ClienteLLM,
        url: str,
        tabla: str = "fragmentos",
        timeout: int = 5,
        **kwargs,
    ):
        """`timeout`: segundos para conectar. Sin él, una base caída puede tardar minutos en
        dar error."""
        import psycopg
        from pgvector.psycopg import register_vector

        super().__init__(cliente, **kwargs)
        if not tabla.isidentifier():
            raise ValueError(f"Nombre de tabla no válido: {tabla!r}")
        self.tabla = tabla
        self.conexion = psycopg.connect(url, autocommit=True, connect_timeout=timeout)
        self.conexion.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self.conexion)

    @property
    def dimensiones(self) -> int:
        fila = self.conexion.execute(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = to_regclass(%s) AND attname = 'embedding'",
            (self.tabla,),
        ).fetchone()
        return fila[0] if fila else 0

    def vaciar(self) -> None:
        self.conexion.execute(f"DROP TABLE IF EXISTS {self.tabla}")
        self.fragmentos = []

    def añadir(self, fragmentos: Sequence[Fragmento]) -> None:
        vectores = self._vectores([self.prefijo_documento + f.para_indexar() for f in fragmentos])
        self.conexion.execute(
            f"CREATE TABLE IF NOT EXISTS {self.tabla} ("
            "id text PRIMARY KEY, doc text, titulo text, texto text, "
            f"embedding vector({vectores.shape[1]}))"
        )
        with self.conexion.cursor() as cursor:
            cursor.executemany(
                f"INSERT INTO {self.tabla} (id, doc, titulo, texto, embedding) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET "
                "doc = EXCLUDED.doc, titulo = EXCLUDED.titulo, texto = EXCLUDED.texto, "
                "embedding = EXCLUDED.embedding",
                [
                    (f.id, f.doc, f.titulo, f.texto, v)
                    for f, v in zip(fragmentos, vectores, strict=True)
                ],
            )
        self.conexion.execute(
            f"CREATE INDEX IF NOT EXISTS {self.tabla}_hnsw ON {self.tabla} "
            "USING hnsw (embedding vector_cosine_ops)"
        )
        self.fragmentos += list(fragmentos)

    def buscar(self, consulta: str, k: int = 3) -> list[Resultado]:
        vector = self._vectores([self.prefijo_consulta + consulta])[0]
        filas = self.conexion.execute(
            f"SELECT id, doc, titulo, texto, 1 - (embedding <=> %s) AS similitud "
            f"FROM {self.tabla} ORDER BY embedding <=> %s LIMIT %s",
            (vector, vector, k),
        ).fetchall()
        return [
            Resultado(fragmento=Fragmento(id=i, doc=d, titulo=t, texto=x), puntuacion=float(s))
            for i, d, t, x, s in filas
        ]


def tokenizar(texto: str) -> list[str]:
    """Palabras en minúsculas y sin tildes, sin las palabras vacías de `VACIAS`."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return [p for p in PALABRA.findall(sin_tildes) if p not in VACIAS]


class IndiceLexico:
    """Búsqueda por palabras con BM25, la puntuación clásica de los buscadores.

    Premia los fragmentos que contienen las palabras de la consulta, más cuanto más raras
    son esas palabras en el corpus (IDF) y sin premiar de más las repeticiones (`k1`) ni los
    fragmentos largos (`b`). No entiende sinónimos, pero no se le escapa un identificador.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.fragmentos: list[Fragmento] = []
        self._frecuencias: list[Counter[str]] = []
        self._longitudes: list[int] = []
        self._documentos_con: Counter[str] = Counter()

    def añadir(self, fragmentos: Sequence[Fragmento]) -> None:
        for f in fragmentos:
            palabras = tokenizar(f.para_indexar())
            self._frecuencias.append(Counter(palabras))
            self._longitudes.append(len(palabras))
            self._documentos_con.update(set(palabras))
        self.fragmentos += list(fragmentos)

    def _idf(self, palabra: str) -> float:
        n, total = self._documentos_con[palabra], len(self.fragmentos)
        return math.log((total - n + 0.5) / (n + 0.5) + 1)

    def buscar(self, consulta: str, k: int = 3) -> list[Resultado]:
        """Los `k` mejores con puntuación mayor que 0: puede devolver menos, o ninguno."""
        palabras = set(tokenizar(consulta))
        media = sum(self._longitudes) / len(self._longitudes)
        puntuaciones = []
        for frecuencias, longitud in zip(self._frecuencias, self._longitudes, strict=True):
            normalizacion = self.k1 * (1 - self.b + self.b * longitud / media)
            puntuaciones.append(
                sum(
                    self._idf(p) * frecuencias[p] * (self.k1 + 1) / (frecuencias[p] + normalizacion)
                    for p in palabras
                    if p in frecuencias
                )
            )
        orden = sorted(range(len(puntuaciones)), key=lambda i: -puntuaciones[i])
        return [
            Resultado(fragmento=self.fragmentos[i], puntuacion=puntuaciones[i])
            for i in orden[:k]
            if puntuaciones[i] > 0
        ]


def fusion_rrf(listas: Sequence[Sequence[Resultado]], k: int = 3, c: int = 60) -> list[Resultado]:
    """Reciprocal Rank Fusion: combina rankings por posición, no por puntuación.

    Cada fragmento suma 1 / (c + posición) por cada lista en la que aparece. Así se pueden
    mezclar puntuaciones que no son comparables (coseno y BM25). `c` = 60 es el valor del
    paper original; amortigua la ventaja de los primeros puestos.
    """
    puntos: dict[str, float] = {}
    fragmentos: dict[str, Fragmento] = {}
    for lista in listas:
        for posicion, r in enumerate(lista, 1):
            puntos[r.fragmento.id] = puntos.get(r.fragmento.id, 0.0) + 1 / (c + posicion)
            fragmentos[r.fragmento.id] = r.fragmento
    mejores = sorted(puntos, key=lambda i: -puntos[i])[:k]
    return [Resultado(fragmento=fragmentos[i], puntuacion=puntos[i]) for i in mejores]


class IndiceHibrido:
    """Búsqueda densa y léxica a la vez, fusionadas con RRF."""

    def __init__(self, denso: IndiceVectorial, lexico: IndiceLexico, candidatos: int = 20):
        self.denso = denso
        self.lexico = lexico
        self.candidatos = candidatos

    def añadir(self, fragmentos: Sequence[Fragmento]) -> None:
        self.denso.añadir(fragmentos)
        self.lexico.añadir(fragmentos)

    def buscar(self, consulta: str, k: int = 3) -> list[Resultado]:
        return fusion_rrf(
            [
                self.denso.buscar(consulta, self.candidatos),
                self.lexico.buscar(consulta, self.candidatos),
            ],
            k=k,
        )

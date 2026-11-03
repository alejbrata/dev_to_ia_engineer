"""Lección 07: ingesta de documentos reales. PDF con tablas, DOCX, copias y versiones viejas.

La documentación de `datos/empresa/originales/` (la genera `generar_empresa.py`) es la de este
módulo como suele estar en una empresa. Cuatro formas de ingerirla, cada una sobre la anterior:

1. ingenua: el texto de cada fichero tal como sale (pypdf para PDF, los párrafos para DOCX).
2. con tablas: las tablas de PDF (pdfplumber) y DOCX convertidas en filas con su cabecera, y
   las secciones de DOCX como secciones de Markdown.
3. sin duplicados: fuera los documentos que repiten el contenido de otro.
4. solo vigentes: de cada familia de documentos, solo la versión más reciente (manifiesto).

Para cada una, con las 11 preguntas de `datos/empresa/preguntas.jsonl`: si la evidencia llega
a los 3 fragmentos recuperados, si el modelo de 1,5B responde bien, y cuántas veces llega al
contexto un documento obsoleto o un fragmento repetido. Aquí todos los documentos son visibles:
los permisos van en la lección 08.

Uso: `uv run python modulos/03-rag/ingesta_real.py`
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

from curso_core import ClienteLLM, Opciones, prompts
from curso_core.rag import Fragmento, IndiceVectorial, Resultado, trocear_por_secciones

AQUI = Path(__file__).resolve().parent
EMPRESA = AQUI / "datos" / "empresa"
ORIGINALES = EMPRESA / "originales"
K = 3
PARECIDO = 0.8  # proporción de trozos de texto en común para tratar dos documentos como copias
OPCIONES = Opciones(temperatura=0, max_tokens=200)


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.split())


def contiene(texto: str, frase: str) -> bool:
    """La frase está en el texto, sin partir números ni palabras: "200 euros" no está en
    "4.200 euros"."""
    patron = rf"(?<![\w.,]){re.escape(normalizar(frase))}(?!\w)"
    return re.search(patron, normalizar(texto)) is not None


# 1. Extraer el texto


def extraer_ingenuo(ruta: Path) -> str:
    """Lo primero que se le ocurre a cualquiera: el texto tal cual."""
    if ruta.suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(p.extract_text() for p in PdfReader(ruta).pages)
    if ruta.suffix == ".docx":
        from docx import Document

        return "\n".join(p.text for p in Document(str(ruta)).paragraphs)
    return ruta.read_text(encoding="utf-8")


def filas_como_texto(filas: list[list[str | None]]) -> str:
    """Cada fila de una tabla, con su cabecera: "Proveedor: Mensatel; Coste mensual: 850"."""
    limpiar = lambda c: " ".join((c or "").split())  # noqa: E731
    cabecera = [limpiar(c) for c in filas[0]]
    return "\n".join(
        "; ".join(f"{c}: {limpiar(v)}" for c, v in zip(cabecera, fila, strict=False)) + "."
        for fila in filas[1:]
    )


def extraer_con_tablas(ruta: Path) -> str:
    """Las tablas como filas con su cabecera, y la estructura del DOCX como Markdown."""
    if ruta.suffix == ".pdf":
        import pdfplumber

        partes = []
        with pdfplumber.open(ruta) as pdf:
            for pagina in pdf.pages:
                tablas = pagina.find_tables()
                fuera = pagina
                for t in tablas:
                    fuera = fuera.outside_bbox(t.bbox)  # el texto que no está en tablas
                partes.append(fuera.extract_text())
                partes += [filas_como_texto(t.extract()) for t in tablas]
        return "\n\n".join(partes)
    if ruta.suffix == ".docx":
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        documento, partes = Document(str(ruta)), []
        for bloque in documento.iter_inner_content():  # párrafos y tablas, en su orden
            if isinstance(bloque, Table):
                partes.append(filas_como_texto([[c.text for c in f.cells] for f in bloque.rows]))
            elif isinstance(bloque, Paragraph) and bloque.text.strip():
                nivel = bloque.style.name.removeprefix("Heading ")
                prefijo = "#" * int(nivel) + " " if nivel.isdigit() else ""
                partes.append(prefijo + bloque.text)
        return "\n\n".join(partes)
    return ruta.read_text(encoding="utf-8")


# 2. Copias y versiones


def trozos(texto: str, n: int = 5) -> set[str]:
    """Las secuencias de n palabras del texto: lo que se compara para encontrar copias."""
    palabras = re.findall(r"\w+", normalizar(texto))
    return {" ".join(palabras[i : i + n]) for i in range(max(1, len(palabras) - n + 1))}


def sin_duplicados(textos: dict[str, str]) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Quita los documentos que repiten otro. Se queda con el Markdown, si lo hay, porque
    conserva la estructura. Devuelve los que quedan y los pares (quitado, original)."""
    orden = sorted(textos, key=lambda n: (not n.endswith(".md"), len(n), n))
    quedan: dict[str, str] = {}
    quitados = []
    for nombre in orden:
        t = trozos(textos[nombre])
        copia = next((o for o in quedan if len(t & trozos(quedan[o])) / len(t) >= PARECIDO), None)
        if copia:
            quitados.append((nombre, copia))
        else:
            quedan[nombre] = textos[nombre]
    return {n: textos[n] for n in textos if n in quedan}, quitados


def solo_vigentes(textos: dict[str, str], manifiesto: dict) -> dict[str, str]:
    """De cada familia, el documento con la fecha más reciente."""
    ultima: dict[str, str] = {}
    for nombre in textos:
        familia = manifiesto[nombre]["familia"]
        if (
            familia not in ultima
            or manifiesto[nombre]["fecha"] > manifiesto[ultima[familia]]["fecha"]
        ):
            ultima[familia] = nombre
    return {n: t for n, t in textos.items() if n in ultima.values()}


# 3. Indexar y medir


def fragmentos(textos: dict[str, str], manifiesto: dict) -> list[Fragmento]:
    resultado = []
    for nombre, texto in textos.items():
        if not texto.lstrip().startswith("# "):
            texto = "# " + texto.lstrip()  # la primera línea, como título
        datos = manifiesto[nombre]
        meta = {"fuente": nombre, "familia": datos["familia"], "fecha": str(datos["fecha"])}
        for f in trocear_por_secciones(nombre, texto):
            resultado.append(f.model_copy(update={"meta": meta | {"acceso": datos["acceso"]}}))
    return resultado


def configuraciones(manifiesto: dict) -> dict[str, dict[str, str]]:
    rutas = sorted(ORIGINALES.iterdir())
    ingenua = {r.name: extraer_ingenuo(r) for r in rutas}
    tablas = {r.name: extraer_con_tablas(r) for r in rutas}
    unicos, _ = sin_duplicados(tablas)
    return {
        "ingenua": ingenua,
        "con tablas": tablas,
        "sin duplicados": unicos,
        "solo vigentes": solo_vigentes(unicos, manifiesto),
    }


def repetidos(recuperados: list[Resultado]) -> bool:
    """Si dos de los fragmentos recuperados dicen lo mismo: un hueco del contexto perdido."""
    conjuntos = [trozos(r.fragmento.texto) for r in recuperados]
    return any(
        len(a & b) / min(len(a), len(b)) >= PARECIDO
        for i, a in enumerate(conjuntos)
        for b in conjuntos[i + 1 :]
    )


def medir(cliente: ClienteLLM, textos: dict, manifiesto: dict, preguntas) -> dict:
    vigentes = set(solo_vigentes(textos, manifiesto))
    indice = IndiceVectorial(cliente)
    indice.añadir(fragmentos(textos, manifiesto))
    prompt = prompts.cargar("rag/con-contexto")
    filas = []
    for p in preguntas:
        recuperados: list[Resultado] = indice.buscar(p["pregunta"], K)
        juntos = " ".join(r.fragmento.texto for r in recuperados)
        contexto = "\n\n".join(
            f"[{i}] {r.fragmento.titulo}\n{r.fragmento.texto}" for i, r in enumerate(recuperados, 1)
        )
        texto = cliente.chat(
            prompts.renderizar(prompt, contexto=contexto, pregunta=p["pregunta"]), opciones=OPCIONES
        ).texto
        filas.append(
            {
                "id": p["id"],
                "fuentes": [r.fragmento.meta["fuente"] for r in recuperados],
                "recuperado": all(contiene(juntos, e) for e in p["evidencias"]),
                "correcta": all(contiene(texto, c) for c in p["claves"])
                and not any(contiene(texto, x) for x in p["prohibido"]),
                "obsoleto": any(r.fragmento.meta["fuente"] not in vigentes for r in recuperados),
                "repetido": repetidos(recuperados),
                "respuesta": texto.strip(),
            }
        )
    return {"documentos": len(textos), "fragmentos": len(indice.fragmentos), "filas": filas}


def main() -> int:
    with (EMPRESA / "manifiesto.toml").open("rb") as f:
        manifiesto = tomllib.load(f)
    preguntas = [
        json.loads(linea)
        for linea in (EMPRESA / "preguntas.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    configs = configuraciones(manifiesto)

    print("1. La misma tabla, extraída de dos formas (proveedores-2026.pdf)")
    pdf = ORIGINALES / "proveedores-2026.pdf"
    for nombre, texto in (
        ("ingenua", extraer_ingenuo(pdf)),
        ("con tablas", extraer_con_tablas(pdf)),
    ):
        print(f"   {nombre}:")
        linea = next(i for i, x in enumerate(texto.splitlines()) if "Mensatel" in x)
        for x in texto.splitlines()[max(0, linea - 1) : linea + 2]:
            print(f"     | {x}")
    print(
        "   guardias.docx, ingenua: ¿está la tabla de compensación?",
        "sí" if "150 euros" in configs["ingenua"]["guardias.docx"] else "no",
    )

    _, quitados = sin_duplicados(configs["con tablas"])
    print("\n2. Copias encontradas por contenido")
    for copia, original in quitados:
        print(f"   {copia!r} repite {original!r}")

    cliente = ClienteLLM()
    print(f"\n3. Recuperación y respuestas, {len(preguntas)} preguntas (modelo del rol chat)")
    print(
        f"   {'':15} {'docs':>5} {'frag.':>6} {'evidencia@3':>12} {'correctas':>10}"
        f" {'con obsoleto':>13} {'con repetidos':>14}"
    )
    resultados = {}
    for nombre, textos in configs.items():
        r = resultados[nombre] = medir(cliente, textos, manifiesto, preguntas)
        f = r["filas"]
        print(
            f"   {nombre:15} {r['documentos']:>5} {r['fragmentos']:>6}"
            f" {sum(x['recuperado'] for x in f):>12} {sum(x['correcta'] for x in f):>10}"
            f" {sum(x['obsoleto'] for x in f):>13} {sum(x['repetido'] for x in f):>14}"
        )
    print("   (de 11; con obsoleto: alguno de los 3 fragmentos es de una versión anterior)")
    print("\n4. Pregunta a pregunta: bien (✓) o mal (✗); «o», con un documento obsoleto delante")
    print("   " + " " * 5 + "".join(f"{n:>16}" for n in resultados))
    for i, p in enumerate(preguntas):
        marcas = []
        for r in resultados.values():
            f = r["filas"][i]
            marcas.append(("✓" if f["correcta"] else "✗") + (" o" if f["obsoleto"] else "  "))
        print(f"   {p['id']:5}" + "".join(f"{m:>16}" for m in marcas))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""El mismo índice, en PostgreSQL con pgvector: persistente y consultable con SQL.

1. Indexa las secciones en PostgreSQL (o reutiliza lo indexado en una ejecución anterior).
2. Compara la recuperación y la latencia con el índice en memoria de numpy.
3. Enseña el plan de ejecución de la consulta.
4. Consulta con un vector de otro modelo: aquí el error lo da la base de datos.

Necesita la base de datos del repo: `docker compose up -d`.
Uso: `uv run python modulos/03-rag/indice_pgvector.py [--reindexar]`
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

import corpus
import psycopg
from curso_core import ClienteLLM
from curso_core.config import cargar
from curso_core.metrics import mrr, recall_at_k
from curso_core.rag import IndicePgvector, IndiceVectorial, trocear_por_secciones

K = 3
URL_POR_DEFECTO = "postgresql://curso:curso@127.0.0.1:5433/curso"
VECTOR_LITERAL = re.compile(r"'\[[^\]]*\]'::vector")


def medir(indice: IndiceVectorial, preguntas: list[corpus.Pregunta]) -> tuple[float, float, float]:
    """recall@3, MRR y milisegundos por búsqueda (incluye calcular el embedding de la pregunta)."""
    inicio = time.perf_counter()
    resultados = [indice.buscar(p.pregunta, K) for p in preguntas]
    ms = (time.perf_counter() - inicio) * 1000 / len(preguntas)
    relevantes = [
        [corpus.es_relevante(r.fragmento, p) for r in rs]
        for p, rs in zip(preguntas, resultados, strict=True)
    ]
    return recall_at_k(relevantes, K), mrr(relevantes), ms


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reindexar", action="store_true", help="borra la tabla y la rehace")
    args = parser.parse_args()

    cargar()
    url = os.environ.get("PGVECTOR_URL", URL_POR_DEFECTO)
    cliente = ClienteLLM()
    try:
        pg = IndicePgvector(cliente, url)
    except psycopg.OperationalError as e:
        print(f"No hay base de datos en {url}.\n{e}\nLevántala con: docker compose up -d")
        return 1

    trozos = [f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)]
    preguntas = [p for p in corpus.preguntas() if p.respondible]

    print("1. Indexar en PostgreSQL")
    if args.reindexar:
        pg.vaciar()
    guardados = pg.dimensiones and pg.conexion.execute("SELECT count(*) FROM fragmentos").fetchone()
    if guardados:
        print(f"   ya indexado: {guardados[0]} fragmentos de {pg.dimensiones} dimensiones")
        print("   (sigue ahí tras reiniciar el script o el contenedor; --reindexar lo rehace)")
    else:
        inicio = time.perf_counter()
        pg.añadir(trozos)
        print(f"   {len(trozos)} fragmentos indexados en {time.perf_counter() - inicio:.1f} s")

    print("\n2. Misma búsqueda, dos índices (26 preguntas)")
    memoria = IndiceVectorial(cliente)
    memoria.añadir(trozos)
    for nombre, indice in [("numpy, en memoria", memoria), ("pgvector", pg)]:
        recall, orden, ms = medir(indice, preguntas)
        print(f"   {nombre:18} recall@3 {recall:4.0%} · MRR {orden:.2f} · {ms:.0f} ms/búsqueda")

    print("\n3. Plan de la consulta")
    vector = memoria._vectores([preguntas[0].pregunta])[0]
    for titulo, ajuste in [
        ("por defecto", "RESET enable_seqscan"),
        ("prohibiendo el recorrido secuencial", "SET enable_seqscan = off"),
    ]:
        pg.conexion.execute(ajuste)
        print(f"   {titulo}:")
        for (linea,) in pg.conexion.execute(
            "EXPLAIN SELECT id FROM fragmentos ORDER BY embedding <=> %s LIMIT 3", (vector,)
        ):
            print("     " + VECTOR_LITERAL.sub("'[...]'::vector", linea))
    pg.conexion.execute("RESET enable_seqscan")

    print("\n4. Consulta con un vector de nomic-embed-text (768 dimensiones)")
    pg.rol = "embeddings_ingles"
    try:
        pg.buscar(preguntas[0].pregunta)
    except psycopg.Error as e:
        print(f"   {type(e).__module__}.{type(e).__name__}: {e}")
    pg.conexion.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

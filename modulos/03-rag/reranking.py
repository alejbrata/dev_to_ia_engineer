"""Reranking: reordenar los candidatos de la búsqueda con un cross-encoder.

1. Densa e híbrida, sin y con reranking: recall, MRR y latencia.
2. Cuántos candidatos reordenar: calidad frente a latencia.
3. Las preguntas que cambian de posición.
4. ¿Separa mejor la puntuación del reranker las preguntas sin respuesta?

Necesita el reranker en llama-server (ver el rol `reranker` en config/models.toml):
`llama-server -hf gpustack/bge-reranker-v2-m3-GGUF:Q8_0 --reranking --port 8082`
Uso: `uv run python modulos/03-rag/reranking.py`
"""

from __future__ import annotations

import sys
import time

import corpus
from curso_core import ClienteLLM, ErrorLLM
from curso_core.metrics import mrr, recall_at_k
from curso_core.rag import (
    IndiceHibrido,
    IndiceLexico,
    IndiceReordenado,
    IndiceVectorial,
    Resultado,
    trocear_por_secciones,
)

K = 3
CANDIDATOS = [5, 10, 20, 40]
UMBRALES = [-4.0, -2.0, 0.0]


def posicion(resultados: list[Resultado], pregunta: corpus.Pregunta) -> int | None:
    """Posición (desde 1) del primer fragmento relevante, o None si no está."""
    return next(
        (i for i, r in enumerate(resultados, 1) if corpus.es_relevante(r.fragmento, pregunta)),
        None,
    )


def medir(indice, preguntas: list[corpus.Pregunta]) -> tuple[dict[int, list[Resultado]], float]:
    inicio = time.perf_counter()
    resultados = {p.id: indice.buscar(p.pregunta, K) for p in preguntas}
    return resultados, (time.perf_counter() - inicio) * 1000 / len(preguntas)


def metricas(resultados: dict[int, list[Resultado]], preguntas: list[corpus.Pregunta]) -> str:
    rel = [[corpus.es_relevante(r.fragmento, p) for r in resultados[p.id]] for p in preguntas]
    return f"{recall_at_k(rel, 1):8.0%}  {recall_at_k(rel, 3):8.0%}  {mrr(rel):5.2f}"


def main() -> int:
    cliente = ClienteLLM()
    try:
        cliente.reordenar("prueba", ["prueba"])
    except ErrorLLM as e:
        print(f"No responde el reranker: {e}\nArráncalo como indica la cabecera de este script.")
        return 1

    trozos = [f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)]
    preguntas = corpus.preguntas()
    respondibles = [p for p in preguntas if p.respondible]
    denso, lexico = IndiceVectorial(cliente), IndiceLexico()
    hibrido = IndiceHibrido(denso, lexico)
    hibrido.añadir(trozos)

    print(f"1. Sin y con reranking de 20 candidatos, {len(respondibles)} preguntas con respuesta")
    print(f"   {'búsqueda':26} recall@1  recall@3    MRR  ms/búsqueda")
    configuraciones = {
        "densa": denso,
        "densa + reranking": IndiceReordenado(denso, cliente),
        "híbrida": hibrido,
        "híbrida + reranking": IndiceReordenado(hibrido, cliente),
    }
    todos: dict[str, dict[int, list[Resultado]]] = {}
    for nombre, indice in configuraciones.items():
        todos[nombre], ms = medir(indice, preguntas)
        print(f"   {nombre:26}{metricas(todos[nombre], respondibles)}  {ms:11.0f}")

    print("\n2. Densa + reranking, según cuántos candidatos se reordenan")
    for n in CANDIDATOS:
        resultados, ms = medir(IndiceReordenado(denso, cliente, candidatos=n), respondibles)
        print(f"   {n:2} candidatos          {metricas(resultados, respondibles)}  {ms:11.0f}")

    print("\n3. Posición del primer fragmento con la respuesta (densa → densa + reranking)")
    for p in respondibles:
        antes = posicion(todos["densa"][p.id], p)
        despues = posicion(todos["densa + reranking"][p.id], p)
        if antes != despues:
            print(f"   {str(antes or '-'):>2} → {str(despues or '-'):<2} {p.id:2}. {p.pregunta}")

    print("\n4. Puntuación del primer resultado tras el reranking")
    primeras = {p.id: todos["densa + reranking"][p.id][0].puntuacion for p in preguntas}
    si = [primeras[p.id] for p in respondibles]
    no = [primeras[p.id] for p in preguntas if not p.respondible]
    print(
        f"   con respuesta {min(si):6.2f} a {max(si):6.2f} · "
        f"sin respuesta {min(no):6.2f} a {max(no):6.2f}"
    )
    for umbral in UMBRALES:
        perdidas = sum(s < umbral for s in si)
        cuelan = sum(s >= umbral for s in no)
        print(
            f"   umbral {umbral:5.1f}: descarta {perdidas} de {len(si)} con respuesta, "
            f"deja pasar {cuelan} de {len(no)} sin respuesta"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

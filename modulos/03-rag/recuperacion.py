"""Recuperación densa, léxica (BM25) e híbrida (RRF), medidas con las mismas preguntas.

1. recall@k, precision@3 y MRR de las tres búsquedas, y lo que tarda cada una.
2. Las preguntas en las que una acierta y la otra no.
3. Las preguntas sin respuesta: ¿sirve un umbral de puntuación para detectarlas?

Uso: `uv run python modulos/03-rag/recuperacion.py`
"""

from __future__ import annotations

import sys
import time

import corpus
from curso_core import ClienteLLM
from curso_core.metrics import mrr, precision_at_k, recall_at_k
from curso_core.rag import (
    IndiceHibrido,
    IndiceLexico,
    IndiceVectorial,
    Resultado,
    trocear_por_secciones,
)

K = 5
UMBRALES = [0.55, 0.60, 0.65]
IDENTIFICADORES = ["invalid_grant", "OPENSEARCH_URL", "precios_desde_principal", "perfil_edicion"]


def main() -> int:
    cliente = ClienteLLM()
    trozos = [f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)]
    preguntas = corpus.preguntas()
    respondibles = [p for p in preguntas if p.respondible]

    denso = IndiceVectorial(cliente)
    lexico = IndiceLexico()
    hibrido = IndiceHibrido(denso, lexico)
    hibrido.añadir(trozos)
    indices = {"densa (bge-m3)": denso, "léxica (BM25)": lexico, "híbrida (RRF)": hibrido}

    print(f"1. Recuperación, {len(respondibles)} preguntas con respuesta")
    print(f"   {'búsqueda':16} recall@1  recall@3  recall@5  precision@3   MRR  ms/búsqueda")
    resultados: dict[str, dict[int, list[Resultado]]] = {}
    for nombre, indice in indices.items():
        inicio = time.perf_counter()
        resultados[nombre] = {p.id: indice.buscar(p.pregunta, K) for p in preguntas}
        ms = (time.perf_counter() - inicio) * 1000 / len(preguntas)
        rel = [
            [corpus.es_relevante(r.fragmento, p) for r in resultados[nombre][p.id]]
            for p in respondibles
        ]
        recalls = "  ".join(f"{recall_at_k(rel, k):8.0%}" for k in (1, 3, 5))
        precision = precision_at_k(rel, 3)
        orden = mrr([r[:3] for r in rel])  # con los 3 primeros, como en las lecciones anteriores
        print(f"   {nombre:16}{recalls}  {precision:11.0%}  {orden:4.2f}  {ms:11.1f}")

    print("\n2. Aciertos en el top 3 que solo consigue una de las dos")
    densa, lexica = resultados["densa (bge-m3)"], resultados["léxica (BM25)"]
    for p in respondibles:
        en_densa = any(corpus.es_relevante(r.fragmento, p) for r in densa[p.id][:3])
        en_lexica = any(corpus.es_relevante(r.fragmento, p) for r in lexica[p.id][:3])
        if en_densa != en_lexica:
            gana = "densa " if en_densa else "léxica"
            print(f"   solo {gana}  {p.id:2}. {p.pregunta}")

    print("\n3. Puntuación del primer resultado: con respuesta frente a sin respuesta")
    for nombre in indices:
        primeras = {p.id: (resultados[nombre][p.id] or [None])[0] for p in preguntas}
        si = [primeras[p.id].puntuacion for p in respondibles if primeras[p.id]]
        no = [
            primeras[p.id].puntuacion if primeras[p.id] else 0.0
            for p in preguntas
            if not p.respondible
        ]
        print(
            f"   {nombre:16} con respuesta {min(si):6.3f} a {max(si):6.3f} · "
            f"sin respuesta {min(no):6.3f} a {max(no):6.3f}"
        )
    print("   Umbral sobre la similitud densa del primer resultado:")
    for umbral in UMBRALES:
        perdidas = sum(densa[p.id][0].puntuacion < umbral for p in respondibles)
        cuelan = sum(densa[p.id][0].puntuacion >= umbral for p in preguntas if not p.respondible)
        print(
            f"   {umbral:.2f}: descarta {perdidas} de {len(respondibles)} con respuesta, "
            f"deja pasar {cuelan} de {len(preguntas) - len(respondibles)} sin respuesta"
        )

    print("\n4. Consultas con un identificador, como las que se pegan desde un log")
    for consulta in IDENTIFICADORES:
        print(f"   {consulta}")
        for nombre, indice in indices.items():
            mejores = indice.buscar(consulta, 3)
            if not mejores:
                print(f"     {nombre:16} sin resultados")
                continue
            primero = mejores[0]
            marca = "contiene" if consulta in primero.fragmento.texto else "NO contiene"
            print(
                f"     {nombre:16} {primero.fragmento.id:28} {primero.puntuacion:6.3f}  "
                f"({marca} el identificador · resultados: {len(mejores)})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())

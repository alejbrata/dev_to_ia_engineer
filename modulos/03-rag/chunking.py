"""Ingesta y chunking: cuatro formas de trocear la misma documentación, medidas.

Para cada estrategia indexa los fragmentos con bge-m3 y mide, con las 26 preguntas que
tienen respuesta:

- evidencias partidas: frases clave que no caben enteras en ningún fragmento;
- recall@3: preguntas con al menos un fragmento relevante entre los 3 primeros;
- MRR: lo arriba que sale el primer fragmento relevante;
- tokens de contexto: lo que ocupan, de media, los 3 fragmentos recuperados.

Uso: `uv run python modulos/03-rag/chunking.py`
"""

from __future__ import annotations

import sys
from collections.abc import Callable

import corpus
from curso_core import ClienteLLM
from curso_core.metrics import mrr, recall_at_k
from curso_core.rag import Fragmento, IndiceVectorial, trocear_fijo, trocear_por_secciones

K = 3

ESTRATEGIAS: dict[str, Callable[[str, str], list[Fragmento]]] = {
    "secciones de Markdown": trocear_por_secciones,
    "fijo, 50 palabras": lambda d, t: trocear_fijo(d, t, palabras=50),
    "fijo, 50 palabras, solape 15": lambda d, t: trocear_fijo(d, t, palabras=50, solape=15),
    "fijo, 200 palabras": lambda d, t: trocear_fijo(d, t, palabras=200),
}


def evidencias_partidas(fragmentos: list[Fragmento], preguntas: list[corpus.Pregunta]) -> list:
    """Evidencias que no aparecen enteras en ningún fragmento: el troceado las ha cortado."""
    return [
        (p.id, e)
        for p in preguntas
        for e in p.evidencias
        if not any(e in f.texto for f in fragmentos)
    ]


def main() -> int:
    preguntas = [p for p in corpus.preguntas() if p.respondible]
    documentos = corpus.documentos()
    cliente = ClienteLLM()
    print(
        f"{'estrategia':30} {'fragmentos':>10} {'partidas':>9} {'recall@3':>9} {'MRR':>6} ", end=""
    )
    print(f"{'tokens':>7}")
    ejemplos = []
    for nombre, trocear in ESTRATEGIAS.items():
        fragmentos = [f for doc, texto in documentos.items() for f in trocear(doc, texto)]
        partidas = evidencias_partidas(fragmentos, preguntas)
        indice = IndiceVectorial(cliente)
        indice.añadir(fragmentos)
        resultados = [indice.buscar(p.pregunta, K) for p in preguntas]
        relevantes = [
            [corpus.es_relevante(r.fragmento, p) for r in rs]
            for p, rs in zip(preguntas, resultados, strict=True)
        ]
        palabras = sum(len(r.fragmento.texto.split()) for rs in resultados for r in rs)
        tokens = round(palabras / len(preguntas) * 1.4)  # ~1,4 tokens por palabra (módulo 1)
        print(
            f"{nombre:30} {len(fragmentos):>10} {len(partidas):>9} "
            f"{recall_at_k(relevantes, K):>9.0%} {mrr(relevantes):>6.2f} {tokens:>7}"
        )
        ejemplos += [(nombre, pid, e) for pid, e in partidas[:2]]

    print("\nEvidencias partidas (ejemplos):")
    for nombre, pid, evidencia in ejemplos:
        print(f"  [{nombre}] pregunta {pid}: {evidencia!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

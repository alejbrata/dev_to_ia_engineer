"""Embeddings: qué modelo usas importa, y tiene que ser el mismo al indexar y al consultar.

1. Compara la recuperación con tres configuraciones: bge-m3 (multilingüe), nomic-embed-text
   (entrenado sobre todo en inglés) sin prefijos y con los prefijos que pide su ficha.
2. Muestra la similitud entre frases que dicen lo mismo y frases que no.
3. Indexa con un modelo y consulta con otro, como pasa cuando alguien cambia el modelo de
   embeddings en la configuración y no reindexa.

Uso: `uv run python modulos/03-rag/embeddings.py`
"""

from __future__ import annotations

import sys

import corpus
import numpy as np
from curso_core import ClienteLLM
from curso_core.metrics import mrr, recall_at_k
from curso_core.rag import IndiceVectorial, trocear_por_secciones

K = 3
FRASES = [
    "La base de datos de cobros no acepta más conexiones.",
    "too many connections contra Postgres en pagos",
    "El email de bienvenida tiene una errata.",
]


def fragmentos():
    return [f for doc, t in corpus.documentos().items() for f in trocear_por_secciones(doc, t)]


def medir(indice: IndiceVectorial, preguntas: list[corpus.Pregunta]) -> tuple[float, float]:
    relevantes = [
        [corpus.es_relevante(r.fragmento, p) for r in indice.buscar(p.pregunta, K)]
        for p in preguntas
    ]
    return recall_at_k(relevantes, K), mrr(relevantes)


def main() -> int:
    cliente = ClienteLLM()
    preguntas = [p for p in corpus.preguntas() if p.respondible]
    trozos = fragmentos()

    print("1. Recuperación con secciones, 26 preguntas")
    configuraciones = {
        "bge-m3": IndiceVectorial(cliente, rol="embeddings"),
        "nomic-embed-text, sin prefijos": IndiceVectorial(cliente, rol="embeddings_ingles"),
        "nomic-embed-text, con prefijos": IndiceVectorial(
            cliente,
            rol="embeddings_ingles",
            prefijo_documento="search_document: ",
            prefijo_consulta="search_query: ",
        ),
    }
    for nombre, indice in configuraciones.items():
        indice.añadir(trozos)
        recall, orden = medir(indice, preguntas)
        dimensiones = indice.dimensiones
        print(
            f"   {nombre:32} recall@3 {recall:4.0%} · MRR {orden:.2f} · {dimensiones} dimensiones"
        )

    print("\n2. Similitud del coseno entre frases (bge-m3)")
    vectores = np.array(cliente.embeber(FRASES).vectores)
    vectores /= np.linalg.norm(vectores, axis=1, keepdims=True)
    print(f"   misma idea, otras palabras: {vectores[0] @ vectores[1]:.3f}")
    print(f"   ideas distintas:            {vectores[0] @ vectores[2]:.3f}")

    print("\n3. Índice con bge-m3, consulta con otro modelo (alguien cambia la configuración)")
    indice = configuraciones["bge-m3"]
    indice.rol = "embeddings_ingles"  # 768 dimensiones frente a 1024
    try:
        indice.buscar(preguntas[0].pregunta)
    except ValueError as e:
        print(f"   con nomic-embed-text -> ValueError: {e}")
    indice.rol = "embeddings_otro"  # qwen3-embedding: también 1024 dimensiones
    recall, orden = medir(indice, preguntas)
    print(f"   con qwen3-embedding  -> sin error · recall@3 {recall:4.0%} · MRR {orden:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

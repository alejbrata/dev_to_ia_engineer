"""Exporta el espacio de embeddings del corpus del módulo 3 para el laboratorio de la web.

Calcula con el rol `embeddings` (bge-m3) los vectores de las secciones y de las preguntas,
los proyecta a 2D con PCA para dibujarlos y guarda, para cada pregunta, sus vecinos más
cercanos calculados en todas las dimensiones. Escribe site/src/data/embeddings.json.

Necesita Ollama con el modelo de embeddings. Uso: `uv run python scripts/datos_embeddings.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "modulos" / "03-rag"))

import corpus  # noqa: E402
from curso_core import ClienteLLM  # noqa: E402
from curso_core.rag import IndiceVectorial, trocear_por_secciones  # noqa: E402

SALIDA = RAIZ / "site" / "src" / "data" / "embeddings.json"
VECINOS = 5
GRUPOS = {"runbook": "runbook", "postmortem": "postmortem", "arquitectura": "arquitectura"}


def main() -> None:
    cliente = ClienteLLM()
    trozos = [f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)]
    preguntas = corpus.preguntas()

    indice = IndiceVectorial(cliente)
    indice.añadir(trozos)
    docs = indice._matriz
    consultas = indice._vectores([p.pregunta for p in preguntas])

    # PCA sobre las secciones: los dos ejes en los que más varían los vectores.
    media = docs.mean(axis=0)
    _, valores, ejes = np.linalg.svd(docs - media, full_matrices=False)
    varianza = (valores**2) / (valores**2).sum()
    plano = ejes[:2].T

    def proyectar(m: np.ndarray) -> list[list[float]]:
        return np.round((m - media) @ plano, 4).tolist()

    similitudes = consultas @ docs.T
    datos = {
        "modelo_dimensiones": int(docs.shape[1]),
        "varianza_2d": round(float(varianza[:2].sum()), 3),
        "fragmentos": [
            {
                "id": f.id,
                "titulo": f.titulo,
                "grupo": GRUPOS.get(f.doc.split("-")[0], "otros"),
                "xy": xy,
            }
            for f, xy in zip(trozos, proyectar(docs), strict=True)
        ],
        "preguntas": [
            {
                "id": p.id,
                "texto": p.pregunta,
                "respondible": p.respondible,
                "xy": xy,
                "vecinos": [
                    {"i": int(i), "s": round(float(fila[i]), 3)}
                    for i in np.argsort(-fila)[:VECINOS]
                ],
                "relevantes": [i for i, f in enumerate(trozos) if corpus.es_relevante(f, p)],
            }
            for p, xy, fila in zip(preguntas, proyectar(consultas), similitudes, strict=True)
        ],
    }
    SALIDA.write_text(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"Escrito {SALIDA.relative_to(RAIZ)}: {len(trozos)} fragmentos, {len(preguntas)} "
        f"preguntas, varianza en 2D {datos['varianza_2d']:.1%}"
    )


if __name__ == "__main__":
    main()

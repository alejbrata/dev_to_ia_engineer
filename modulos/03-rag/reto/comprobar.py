"""Comprueba el reto del módulo 3: indexa con tu troceado y mide tu búsqueda con las 26
preguntas con respuesta. Solo usa el modelo de embeddings: de 1 a 3 minutos en CPU.

Uso: `uv run python modulos/03-rag/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from curso_core.metrics import mrr, recall_at_k
from curso_core.retos import Criterio, cargar, elegir, informe

AQUI = Path(__file__).resolve().parent
K = 3
MINIMOS = {"recall@3": 0.80, "MRR": 0.65}
TOKENS_MAXIMOS = 250  # de contexto por pregunta: sin esto, trozos enormes "arreglan" el recall


def medir(m, cliente) -> dict:
    """Las métricas de la 3.02, con el troceado y la búsqueda del alumno."""
    preguntas = [p for p in m.corpus.preguntas() if p.respondible]
    indice = m.indexar(cliente, m.corpus.documentos())
    resultados = [m.buscar(indice, p.pregunta, K) for p in preguntas]
    relevantes = [
        [m.corpus.es_relevante(r.fragmento, p) for r in rs]
        for p, rs in zip(preguntas, resultados, strict=True)
    ]
    palabras = sum(len(r.fragmento.texto.split()) for rs in resultados for r in rs)
    return {
        "fragmentos": len(indice.fragmentos),
        "recall@3": recall_at_k(relevantes, K),
        "MRR": mrr(relevantes),
        "tokens": round(palabras / len(preguntas) * 1.4),  # ~1,4 tokens por palabra (módulo 1)
        "vacias": sum(len(rs) < K for rs in resultados),
        "preguntas": len(preguntas),
    }


def criterios(r: dict) -> list[Criterio]:
    n = r["preguntas"]
    return [
        Criterio(
            f"cada búsqueda devuelve {K} fragmentos",
            r["vacias"] == 0,
            f"{r['vacias']} de {n} preguntas con menos" if r["vacias"] else "",
        ),
        *[
            Criterio(f"{nombre} de al menos {minimo:.2f}", r[nombre] >= minimo, f"{r[nombre]:.2f}")
            for nombre, minimo in MINIMOS.items()
        ],
        Criterio(
            f"como mucho {TOKENS_MAXIMOS} tokens de contexto por pregunta",
            r["tokens"] <= TOKENS_MAXIMOS,
            f"{r['tokens']}",
        ),
    ]


def main() -> int:
    from curso_core import ClienteLLM

    ruta, _ = elegir(AQUI, "buscador.py", __doc__.splitlines()[0])
    inicio = time.perf_counter()
    r = medir(cargar(ruta), ClienteLLM())
    titulo = (
        f"Reto del módulo 3 · {ruta.relative_to(AQUI.parent).as_posix()}"
        f" · {r['fragmentos']} fragmentos · {time.perf_counter() - inicio:.0f} s"
    )
    return informe(titulo, criterios(r))


if __name__ == "__main__":
    sys.exit(main())

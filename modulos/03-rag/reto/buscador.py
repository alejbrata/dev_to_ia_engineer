"""Reto del módulo 3: el RAG que no encuentra.

La recuperación del asistente de documentación (los mismos documentos y las mismas 26
preguntas con respuesta del módulo) falla más de lo que debería. Este script trocea los
documentos, los indexa con el modelo de embeddings del rol `embeddings` y busca los 3
fragmentos más parecidos a cada pregunta.

Tiene fallos. `comprobar.py` dice qué criterios no cumple; arréglalo hasta que los cumpla todos.
Puedes cambiar cómo se trocea, qué se indexa y cómo se busca, pero no el modelo de embeddings
ni las preguntas.

Uso: `uv run python modulos/03-rag/reto/buscador.py`
Comprobar: `uv run python modulos/03-rag/reto/comprobar.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

from curso_core import ClienteLLM
from curso_core.rag import Fragmento, IndiceVectorial, Resultado

# corpus.py (los documentos y las preguntas del módulo) está en la carpeta del módulo.
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "03-rag")))
import corpus  # noqa: E402

K = 3
SIMILITUD_MINIMA = 0.75  # por debajo, el fragmento no se parece lo bastante a la pregunta


def trocear(doc: str, texto: str) -> list[Fragmento]:
    """Un fragmento por línea con contenido: así ninguno es demasiado largo."""
    return [
        Fragmento(id=f"{doc}:{i}", doc=doc, titulo="", texto=linea.strip())
        for i, linea in enumerate(texto.splitlines())
        if linea.strip()
    ]


def indexar(cliente: ClienteLLM, documentos: dict[str, str]) -> IndiceVectorial:
    indice = IndiceVectorial(cliente, rol="embeddings")
    indice.añadir([f for doc, texto in documentos.items() for f in trocear(doc, texto)])
    return indice


def buscar(indice: IndiceVectorial, pregunta: str, k: int = K) -> list[Resultado]:
    """Los k fragmentos más parecidos a la pregunta que pasan el umbral de similitud."""
    return [r for r in indice.buscar(pregunta, k) if r.puntuacion >= SIMILITUD_MINIMA]


def main() -> int:
    indice = indexar(ClienteLLM(), corpus.documentos())
    print(f"{len(indice.fragmentos)} fragmentos indexados")
    for p in [p for p in corpus.preguntas() if p.respondible][:3]:
        print(f"\n{p.pregunta}")
        for r in buscar(indice, p.pregunta):
            print(f"   {r.puntuacion:.2f} {r.fragmento.id}: {r.fragmento.texto[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

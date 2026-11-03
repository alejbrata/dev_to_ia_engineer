"""Solución del reto del módulo 3. Los tres cambios están marcados con «Arreglo».

La recuperación del asistente de documentación (los mismos documentos y las mismas 26
preguntas con respuesta del módulo) falla más de lo que debería. Este script trocea los
documentos, los indexa con el modelo de embeddings del rol `embeddings` y busca los 3
fragmentos más parecidos a cada pregunta.

Uso: `uv run python modulos/03-rag/reto/solucion/buscador.py`
Comprobar: `uv run python modulos/03-rag/reto/comprobar.py --solucion`
"""

from __future__ import annotations

import sys
from pathlib import Path

from curso_core import ClienteLLM
from curso_core.rag import Fragmento, IndiceVectorial, Resultado, trocear_por_secciones

# corpus.py (los documentos y las preguntas del módulo) está en la carpeta del módulo.
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "03-rag")))
import corpus  # noqa: E402

K = 3


def trocear(doc: str, texto: str) -> list[Fragmento]:
    """Un fragmento por sección de Markdown, con el título del documento y de la sección."""
    # Arreglo 1: una línea suelta separa cada paso de su condición y cada fila de una tabla de
    # su cabecera. La sección es la unidad que escribió el autor (lección 02).
    # Arreglo 2: trocear_por_secciones pone en `titulo` "documento > sección", y el índice lo
    # embebe con el texto (Fragmento.para_indexar): "Mitigación" sola no dice de qué servicio.
    return trocear_por_secciones(doc, texto)


def indexar(cliente: ClienteLLM, documentos: dict[str, str]) -> IndiceVectorial:
    indice = IndiceVectorial(cliente, rol="embeddings")
    indice.añadir([f for doc, texto in documentos.items() for f in trocear(doc, texto)])
    return indice


def buscar(indice: IndiceVectorial, pregunta: str, k: int = K) -> list[Resultado]:
    """Los k fragmentos más parecidos a la pregunta."""
    # Arreglo 3: con este modelo, un fragmento relevante puede quedarse en 0,6 de similitud. Un
    # umbral fijo sin medir deja preguntas sin contexto. Si hace falta filtrar, se calibra con
    # las preguntas (o se deja al reranker, lección 05).
    return indice.buscar(pregunta, k)


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

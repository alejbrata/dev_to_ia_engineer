"""El sistema que se evalúa en el módulo 4: el RAG del módulo 3.

Búsqueda densa con bge-m3 (opcionalmente con el reranker de la lección 05 del módulo 3),
k fragmentos (3 por defecto) y un prompt del módulo 3 (por defecto, el de citas). Las
prácticas lo llaman a través de `responder`, así que cambiar el sistema es cambiar este
fichero.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03-rag"))

import corpus  # noqa: E402
import generacion  # noqa: E402
from curso_core import ClienteLLM  # noqa: E402
from curso_core.rag import (  # noqa: E402
    Fragmento,
    IndiceReordenado,
    IndiceVectorial,
    trocear_por_secciones,
)

K = 3


class Respuesta(BaseModel):
    texto: str
    citas: list[int] | None
    recuperados: list[Fragmento]


def fragmentos() -> dict[str, Fragmento]:
    """Los fragmentos del corpus por id: los mismos que indexa `indice`."""
    return {f.id: f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)}


def indice(cliente: ClienteLLM, reranker: bool = False) -> IndiceVectorial | IndiceReordenado:
    """El índice denso de las secciones; con `reranker`, reordena 20 candidatos."""
    denso = IndiceVectorial(cliente)
    denso.añadir(list(fragmentos().values()))
    return IndiceReordenado(denso, cliente) if reranker else denso


def responder(
    cliente: ClienteLLM,
    indice: IndiceVectorial | IndiceReordenado,
    pregunta: str,
    prompt: str = "rag/con-citas",
    k: int = K,
    rol: str = "chat",
) -> Respuesta:
    resultados = indice.buscar(pregunta, k)
    # generacion.generar solo usa el texto de la pregunta; el resto de campos no importa.
    p = corpus.Pregunta(
        id=0, pregunta=pregunta, respondible=True, respuesta="", evidencias=[], clave=""
    )
    g = generacion.generar(cliente, prompt, generacion.contexto(resultados), p, rol=rol)
    return Respuesta(texto=g.texto, citas=g.citas, recuperados=[r.fragmento for r in resultados])

"""El sistema que se evalúa en el módulo 4: el RAG del módulo 3.

Búsqueda densa con bge-m3, 3 fragmentos y un prompt del módulo 3 (por defecto, el de citas).
Las prácticas lo llaman a través de `responder`, así que cambiar el sistema es cambiar este
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
from curso_core.rag import Fragmento, IndiceVectorial, trocear_por_secciones  # noqa: E402

K = 3


class Respuesta(BaseModel):
    texto: str
    citas: list[int] | None
    recuperados: list[Fragmento]


def indice(cliente: ClienteLLM) -> IndiceVectorial:
    resultado = IndiceVectorial(cliente)
    resultado.añadir(
        [f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)]
    )
    return resultado


def responder(
    cliente: ClienteLLM, indice: IndiceVectorial, pregunta: str, prompt: str = "rag/con-citas"
) -> Respuesta:
    resultados = indice.buscar(pregunta, K)
    # generacion.generar solo usa el texto de la pregunta; el resto de campos no importa.
    p = corpus.Pregunta(
        id=0, pregunta=pregunta, respondible=True, respuesta="", evidencias=[], clave=""
    )
    g = generacion.generar(cliente, prompt, generacion.contexto(resultados), p)
    return Respuesta(texto=g.texto, citas=g.citas, recuperados=[r.fragmento for r in resultados])

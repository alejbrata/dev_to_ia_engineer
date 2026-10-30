"""Cuándo usar RAG: las mismas 30 preguntas con cuatro estrategias.

1. Sin documentación: el modelo responde con lo que sabe.
2. Toda la documentación en el prompt, con el contexto por defecto del servidor.
3. Toda la documentación en el prompt, con contexto suficiente (8192 tokens).
4. RAG básico: las 3 secciones más parecidas a la pregunta, buscadas por embeddings.

Uso: `uv run python modulos/03-rag/cuando_rag.py`
"""

from __future__ import annotations

import sys
import time

import corpus
from curso_core import ClienteLLM, Opciones, prompts
from curso_core.rag import IndiceVectorial, trocear_por_secciones
from pydantic import BaseModel

OPCIONES = Opciones(temperatura=0, max_tokens=150)
K = 3


class Medida(BaseModel):
    estrategia: str
    aciertos: int = 0
    abstenciones: int = 0
    tokens_entrada: int = 0
    latencia: float = 0.0
    ejemplo: str = ""


def documentacion_completa() -> str:
    return "\n\n".join(corpus.documentos().values())


def medir(
    cliente: ClienteLLM,
    nombre: str,
    preguntas: list[corpus.Pregunta],
    contexto_de,
    opciones: Opciones,
) -> Medida:
    """`contexto_de(pregunta)` devuelve la documentación a incluir, o None si no se incluye."""
    cliente.descargar_modelo()
    sin = prompts.cargar("rag/sin-contexto")
    con = prompts.cargar("rag/con-contexto")
    medida = Medida(estrategia=nombre)
    for p in preguntas:
        contexto = contexto_de(p)
        mensajes = (
            prompts.renderizar(sin, pregunta=p.pregunta)
            if contexto is None
            else prompts.renderizar(con, contexto=contexto, pregunta=p.pregunta)
        )
        r = cliente.chat(mensajes, opciones=opciones)
        correcta = corpus.es_correcta(r.texto, p)
        medida.aciertos += correcta and p.respondible
        medida.abstenciones += correcta and not p.respondible
        medida.tokens_entrada += r.tokens_entrada
        medida.latencia += r.latencia_s
        # La pregunta 7 (SLA de notificaciones) tiene dos versiones en la documentación.
        if p.id == 7:
            medida.ejemplo = r.texto.strip()
    return medida


def main() -> int:
    preguntas = corpus.preguntas()
    cliente = ClienteLLM()
    todo = documentacion_completa()

    inicio = time.perf_counter()
    indice = IndiceVectorial(cliente)
    fragmentos = [
        f for doc, texto in corpus.documentos().items() for f in trocear_por_secciones(doc, texto)
    ]
    indice.añadir(fragmentos)
    print(f"Índice: {len(fragmentos)} secciones en {time.perf_counter() - inicio:.1f} s\n")

    def rag(p: corpus.Pregunta) -> str:
        return "\n\n".join(
            f"[{r.fragmento.titulo}]\n{r.fragmento.texto}" for r in indice.buscar(p.pregunta, K)
        )

    estrategias = [
        ("1. sin documentación", lambda p: None, OPCIONES),
        ("2. todo, contexto por defecto", lambda p: todo, OPCIONES),
        ("3. todo, contexto 8192", lambda p: todo, OPCIONES.model_copy(update={"contexto": 8192})),
        (f"4. RAG (top {K} secciones)", rag, OPCIONES),
    ]
    medidas = [medir(cliente, n, preguntas, c, o) for n, c, o in estrategias]

    si = sum(p.respondible for p in preguntas)  # respondibles
    no = len(preguntas) - si  # sin respuesta en la documentación
    n = len(preguntas)
    print(f"{'estrategia':32} {'aciertos':>9} {'abstiene bien':>13} {'tokens':>7} {'latencia':>9}")
    for m in medidas:
        print(
            f"{m.estrategia:32} {m.aciertos:>5}/{si} {m.abstenciones:>9}/{no} "
            f"{m.tokens_entrada // n:>7} {m.latencia / n:>8.2f}s"
        )
    print(
        "\nRespuesta a '¿Cuál es la disponibilidad comprometida del servicio de notificaciones?':"
    )
    for m in medidas:
        print(f"  [{m.estrategia}] {m.ejemplo!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

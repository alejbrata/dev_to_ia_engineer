"""Tu sistema. Sustituye `responder` por el tuyo: RAG, agente, clasificador...

Todas las llamadas pasan por `curso_core.ClienteLLM`, que deja una traza por llamada
(tokens, latencia, coste) en el fichero que le digas. Los prompts van en prompts/ y los
nombres de modelo en config/models.toml, nunca aquí.
"""

from __future__ import annotations

from pathlib import Path

from curso_core import ClienteLLM, Opciones, prompts

PROMPTS = Path(__file__).resolve().parent / "prompts"
OPCIONES = Opciones(temperatura=0, max_tokens=300)


def responder(cliente: ClienteLLM, entrada: str, rol: str = "chat") -> str:
    mensajes = prompts.renderizar(prompts.cargar("sistema", PROMPTS), entrada=entrada)
    return cliente.chat(mensajes, rol=rol, opciones=OPCIONES).texto.strip()

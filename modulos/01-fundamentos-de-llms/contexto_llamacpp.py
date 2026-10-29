"""El mismo prompt demasiado largo, ahora contra llama.cpp: rechazo en vez de recorte.

Necesita llama-server arrancado (ver la lección 02 del módulo 1):

    llama-server -hf Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M -c 4096 --port 8081

Uso: `uv run python modulos/01-fundamentos-de-llms/contexto_llamacpp.py [párrafos]`
"""

from __future__ import annotations

import sys

import contexto
from curso_core import ClienteLLM, ErrorLLM, Opciones

ROL = "chat_llamacpp"


def main() -> int:
    parrafos = int(sys.argv[1]) if len(sys.argv) > 1 else contexto.PARRAFOS
    cliente = ClienteLLM()
    try:
        r = cliente.chat(
            contexto.construir_prompt(parrafos, dato_al_final=False),
            rol=ROL,
            opciones=Opciones(temperatura=0),
        )
    except ErrorLLM as e:
        print(f"Rechazada · status {e.status} · intentos {e.intentos}")
        print(f"motivo: {e.cuerpo or e}")
        return 1
    print(f"Respuesta: {r.texto.strip()!r} · {r.tokens_entrada} tokens procesados")
    return 0


if __name__ == "__main__":
    sys.exit(main())

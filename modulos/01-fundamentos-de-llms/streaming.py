"""Streaming: el texto llega a trozos y el primero llega mucho antes que el último.

Uso: `uv run python modulos/01-fundamentos-de-llms/streaming.py ["tu pregunta"]`
"""

from __future__ import annotations

import sys

from curso_core import ClienteLLM, Opciones

PREGUNTA = "Explica en cuatro frases qué es una cola de mensajes."


def main() -> int:
    pregunta = " ".join(sys.argv[1:]) or PREGUNTA
    flujo = ClienteLLM().chat_stream(pregunta, opciones=Opciones(temperatura=0))

    print(f"> {pregunta}\n")
    fragmentos = 0
    for fragmento in flujo:
        print(fragmento, end="", flush=True)
        fragmentos += 1

    r = flujo.respuesta
    print(f"\n\n{fragmentos} fragmentos · {r.tokens_salida} tokens de salida")
    print(f"primer fragmento: {r.primer_token_s:.2f} s · respuesta completa: {r.latencia_s:.2f} s")
    velocidad = r.tokens_salida / (r.latencia_s - r.primer_token_s)
    print(f"velocidad de generación: {velocidad:.1f} tokens/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

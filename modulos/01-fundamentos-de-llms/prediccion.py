"""Un LLM predice el siguiente token: míralo token a token.

Pide una respuesta corta con temperatura 0 y muestra, para cada token generado, su
probabilidad y las alternativas que el modelo consideraba.

Uso: `uv run python modulos/01-fundamentos-de-llms/prediccion.py ["tu prompt"]`
"""

from __future__ import annotations

import sys

from curso_core import ClienteLLM, Opciones, TokenGenerado

PROMPT_POR_DEFECTO = "Completa con una sola palabra: el cielo despejado es de color"
ALTERNATIVAS = 4
MAX_TOKENS = 8


def fila(token: TokenGenerado) -> str:
    otras = ", ".join(
        f"{a.token!r} {a.probabilidad:.0%}" for a in token.alternativas if a.token != token.token
    )
    return f"{token.token!r:>14} {token.probabilidad:6.1%}   {otras}"


def main() -> int:
    prompt = " ".join(sys.argv[1:]) or PROMPT_POR_DEFECTO
    respuesta = ClienteLLM().chat(
        prompt,
        opciones=Opciones(temperatura=0, max_tokens=MAX_TOKENS, alternativas=ALTERNATIVAS),
    )
    if respuesta.tokens is None:
        print(f"El proveedor {respuesta.proveedor} no devuelve probabilidades por token.")
        return 1

    print(f"> {prompt}\n")
    print(f"{'token':>14} {'prob.':>6}   alternativas")
    for token in respuesta.tokens:
        print(fila(token))
    print(f"\nRespuesta: {respuesta.texto!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

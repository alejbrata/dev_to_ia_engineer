"""Anatomía de un prompt: tres variantes del mismo prompt, medidas con los mismos tickets.

- `tickets/minimo`: solo el ticket y "clasifícalo".
- `tickets/con-formato`: además, el formato de respuesta y los valores posibles.
- `tickets/completo`: además, rol, contexto y criterios de cada valor.

Para cada variante cuenta las respuestas utilizables (con el formato pedido y valores
válidos) y los aciertos por campo frente a la clasificación esperada.

Uso: `uv run python modulos/02-prompting/anatomia.py [--detalle]`
"""

from __future__ import annotations

import sys

import tickets
from curso_core import ClienteLLM
from medir_prompts import medir, tabla

VARIANTES = ["tickets/minimo", "tickets/con-formato", "tickets/completo"]


def main() -> int:
    casos = tickets.cargar("eval")
    cliente = ClienteLLM()
    medidas = [medir(cliente, v, casos) for v in VARIANTES]

    print(f"Ticket 1: {casos[0].texto}\n")
    for m in medidas:
        print(f"[{m.variante}] primera respuesta:\n{m.ejemplo}\n")

    tabla(medidas, len(casos))
    if "--detalle" in sys.argv:
        for m in medidas[1:]:  # la variante mínima no tiene formato que comparar
            print(f"\n[{m.variante}]")
            print("\n".join(m.detalle))
    return 0


if __name__ == "__main__":
    sys.exit(main())

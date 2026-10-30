"""Few-shot y técnicas populares, medidas con los mismos tickets que la lección 01.

- `tickets/completo`: la referencia (lección 01).
- `tickets/few-shot-2` y `tickets/few-shot-5`: con 2 y 5 ejemplos resueltos.
- `tickets/experto`: "eres el mejor experto del mundo".
- `tickets/paso-a-paso`: razonar antes de responder.
- `tickets/sesgado`: 3 ejemplos, todos de rendimiento (mal ejemplo a propósito).

Uso: `uv run python modulos/02-prompting/few_shot.py [--detalle]`
"""

from __future__ import annotations

import sys
from collections import Counter

import tickets
from curso_core import ClienteLLM
from medir_prompts import OPCIONES, medir, tabla

VARIANTES = [
    "tickets/completo",
    "tickets/few-shot-2",
    "tickets/few-shot-5",
    "tickets/experto",
    "tickets/paso-a-paso",
    "tickets/sesgado",
]
# Razonar necesita espacio: si no, la respuesta se corta antes de las tres líneas.
OPCIONES_RAZONANDO = OPCIONES.model_copy(update={"max_tokens": 600})


def main() -> int:
    casos = tickets.cargar("eval")
    cliente = ClienteLLM()
    medidas = [
        medir(cliente, v, casos, OPCIONES_RAZONANDO if "paso-a-paso" in v else OPCIONES)
        for v in VARIANTES
    ]
    tabla(medidas, len(casos))

    esperadas = Counter(c.esperado.categoria for c in casos)
    print(f"\nTickets que son de rendimiento: {esperadas['rendimiento']} de {len(casos)}")
    for m in medidas:
        predichas = Counter(p.categoria for p in m.predicciones if p)
        salida = m.tokens_salida // len(casos)
        print(
            f"  {m.variante:26} los clasifica como rendimiento: {predichas['rendimiento']:2}",
            end="",
        )
        print(f" · tokens de salida medios: {salida}")

    if "--detalle" in sys.argv:
        for m in medidas:
            print(f"\n[{m.variante}]")
            print("\n".join(m.detalle))
    return 0


if __name__ == "__main__":
    sys.exit(main())

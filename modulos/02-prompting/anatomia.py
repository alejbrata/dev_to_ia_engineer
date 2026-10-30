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
from curso_core import ClienteLLM, Opciones, prompts
from pydantic import BaseModel

VARIANTES = ["tickets/minimo", "tickets/con-formato", "tickets/completo"]
OPCIONES = Opciones(temperatura=0, max_tokens=200)


class Medida(BaseModel):
    variante: str
    utilizables: int = 0
    aciertos: dict[str, int] = {c: 0 for c in tickets.CAMPOS}
    todo_bien: int = 0
    tokens_entrada: int = 0
    latencia: float = 0.0
    ejemplo: str = ""
    detalle: list[str] = []


def medir(cliente: ClienteLLM, variante: str, casos: list[tickets.Ticket]) -> Medida:
    prompt = prompts.cargar(variante)
    medida = Medida(variante=prompt.id)
    for caso in casos:
        r = cliente.chat(prompts.renderizar(prompt, ticket=caso.texto), opciones=OPCIONES)
        predicha = tickets.leer_lineas(r.texto)
        acierto = tickets.aciertos(predicha, caso.esperado)
        medida.utilizables += predicha is not None
        for campo, bien in acierto.items():
            medida.aciertos[campo] += bien
        medida.todo_bien += all(acierto.values())
        medida.tokens_entrada += r.tokens_entrada
        medida.latencia += r.latencia_s
        medida.ejemplo = medida.ejemplo or r.texto.strip()
        e = caso.esperado
        estado = "OK  " if all(acierto.values()) else ("NULO" if predicha is None else "MAL ")
        respuesta = " / ".join(r.texto.strip().splitlines()[:3])
        medida.detalle.append(
            f"{caso.id:3} {estado} esperado {e.categoria}/{e.severidad}/{e.servicio} -> {respuesta}"
        )
    return medida


def main() -> int:
    casos = tickets.cargar("eval")
    cliente = ClienteLLM()
    cliente.chat("Hola.", opciones=Opciones(max_tokens=1))  # calentar el modelo
    medidas = [medir(cliente, v, casos) for v in VARIANTES]

    print(f"Ticket 1: {casos[0].texto}\n")
    for m in medidas:
        print(f"[{m.variante}] primera respuesta:\n{m.ejemplo}\n")

    n = len(casos)
    print(f"{'variante':26} {'utilizables':>11} {'categoría':>9} {'severidad':>9} ", end="")
    print(f"{'servicio':>8} {'las 3':>5} {'tokens':>6} {'latencia':>8}")
    for m in medidas:
        a = m.aciertos
        print(
            f"{m.variante:26} {m.utilizables:>8}/{n} {a['categoria']:>7}/{n} "
            f"{a['severidad']:>7}/{n} {a['servicio']:>6}/{n} {m.todo_bien:>3}/{n} "
            f"{m.tokens_entrada // n:>6} {m.latencia / n:>7.2f}s"
        )
    print("\n(tokens: entrada media por ticket · latencia: media por ticket)")
    if "--detalle" in sys.argv:
        for m in medidas[1:]:  # la variante mínima no tiene formato que comparar
            print(f"\n[{m.variante}]")
            print("\n".join(m.detalle))
    return 0


if __name__ == "__main__":
    sys.exit(main())

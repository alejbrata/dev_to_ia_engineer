"""Salida estructurada: pedir JSON con palabras frente a imponer un esquema.

Dos prompts (`tickets/json-minimo`, que solo pide JSON, y `tickets/json`, el completo
pidiendo JSON), cada uno sin esquema y con el esquema de `Clasificacion` impuesto por el
servidor (`ClienteLLM.extraer`). Al final, el esquema impuesto con muy pocos tokens de
salida: el JSON se corta.

Uso: `uv run python modulos/02-prompting/salida_estructurada.py`
"""

from __future__ import annotations

import sys
from collections import Counter

import tickets
from curso_core import ClienteLLM, ErrorFormato, Opciones, prompts
from medir_prompts import empezar_de_cero

PROMPTS = ["tickets/json-minimo", "tickets/json"]
OPCIONES = Opciones(temperatura=0, max_tokens=200)


def sin_esquema(cliente: ClienteLLM, prompt: prompts.Prompt, casos) -> tuple[Counter, int, str]:
    """Pide JSON solo con el prompt y lo interpreta a mano."""
    empezar_de_cero(cliente)
    resultados, aciertos, ejemplo = Counter(), 0, ""
    for caso in casos:
        r = cliente.chat(prompts.renderizar(prompt, ticket=caso.texto), opciones=OPCIONES)
        predicha, motivo = tickets.leer_json(r.texto)
        resultados[motivo] += 1
        aciertos += predicha == caso.esperado
        ejemplo = ejemplo or r.texto.strip()
    return resultados, aciertos, ejemplo


def con_esquema(cliente: ClienteLLM, prompt: prompts.Prompt, casos) -> tuple[Counter, int, str]:
    """El servidor restringe la respuesta al esquema; extraer la valida."""
    empezar_de_cero(cliente)
    resultados, aciertos, ejemplo = Counter(), 0, ""
    for caso in casos:
        mensajes = prompts.renderizar(prompt, ticket=caso.texto)
        try:
            clasificacion, r = cliente.extraer(mensajes, tickets.Clasificacion, opciones=OPCIONES)
        except ErrorFormato:
            resultados["esquema"] += 1
            continue
        resultados["ok"] += 1
        aciertos += clasificacion == caso.esperado
        ejemplo = ejemplo or r.texto.strip()
    return resultados, aciertos, ejemplo


def truncado(cliente: ClienteLLM, prompt: prompts.Prompt, caso: tickets.Ticket) -> None:
    print("\nEsquema impuesto, pero max_tokens=12:")
    try:
        cliente.extraer(
            prompts.renderizar(prompt, ticket=caso.texto),
            tickets.Clasificacion,
            opciones=OPCIONES.model_copy(update={"max_tokens": 12}),
        )
    except ErrorFormato as e:
        print(f"  motivo de fin: {e.respuesta.motivo_fin} · texto recibido: {e.texto!r}")
        print("  " + "\n  ".join(str(e).splitlines()[:3]))


def main() -> int:
    casos = tickets.cargar("eval")
    cliente = ClienteLLM()
    n = len(casos)
    print(f"{'prompt':22} {'esquema':8} {'válidos':>7} {'JSON inválido':>13} ", end="")
    print(f"{'fuera del esquema':>17} {'las 3':>6}")
    ejemplos = []
    for nombre in PROMPTS:
        prompt = prompts.cargar(nombre)
        for etiqueta, medir in [("no", sin_esquema), ("sí", con_esquema)]:
            r, aciertos, ejemplo = medir(cliente, prompt, casos)
            print(
                f"{prompt.id:22} {etiqueta:8} {r['ok']:>4}/{n} {r['json_invalido']:>10}/{n} "
                f"{r['esquema']:>14}/{n} {aciertos:>3}/{n}"
            )
            ejemplos.append((f"{prompt.id}, esquema {etiqueta}", ejemplo))

    print("\nPrimera respuesta de cada caso:")
    for etiqueta, ejemplo in ejemplos:
        print(f"  [{etiqueta}] {ejemplo!r}")
    truncado(cliente, prompts.cargar("tickets/json"), casos[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

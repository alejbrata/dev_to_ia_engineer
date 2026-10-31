"""Ejecuta el agente en un escenario y muestra su traza paso a paso.

Cada paso es una llamada al modelo: lo que pidió (herramientas y argumentos), lo que le
devolvió el código y, al final, su respuesta. Debajo, lo que hay de verdad en la plataforma.
Es lo primero que hay que mirar cuando un agente falla.

Uso: `uv run python modulos/05-agentes/traza.py ESCENARIO [--herramientas v1|v2] [--razonar]`
"""

from __future__ import annotations

import argparse
import sys
import textwrap

import agente
import plataforma
from curso_core import ClienteLLM

ANCHO = 72  # lo que cabe sin desplazamiento en un bloque de código de la web


def bloque(texto: str, sangria: str, lineas: int = 6) -> str:
    """El texto partido en líneas de ANCHO, sangrado y recortado a unas pocas líneas."""
    partes = []
    for linea in texto.splitlines() or [""]:
        partes += textwrap.wrap(linea, ANCHO - len(sangria)) or [""]
    if len(partes) > lineas:
        partes = partes[:lineas] + ["[...]"]
    return "\n".join(sangria + p for p in partes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("escenario")
    parser.add_argument("--herramientas", choices=["v1", "v2"], default="v2")
    parser.add_argument("--razonar", action="store_true")
    args = parser.parse_args()
    escenario = {e.id: e for e in plataforma.cargar()}[args.escenario]
    versiones = {"v1": plataforma.HERRAMIENTAS_V1, "v2": plataforma.HERRAMIENTAS}
    herramientas = versiones[args.herramientas]

    cliente = ClienteLLM()
    p = plataforma.Plataforma(escenario, plataforma.indice_documentacion(cliente))
    opciones = agente.OPCIONES.model_copy(update={"razonar": args.razonar})
    ej = agente.ejecutar(cliente, p, rol="agente", opciones=opciones, herramientas=herramientas)
    _, _, modelo = cliente.config.resolver("agente")

    print(f"Escenario {escenario.id} · {modelo} · herramientas {args.herramientas}")
    print(f"Alerta: {escenario.alerta}\n")
    for paso in ej.pasos:
        tokens = f"{paso.tokens_entrada} tokens de entrada, {paso.tokens_salida} de salida"
        print(f"paso {paso.n} · {paso.segundos:.1f} s · {tokens}")
        for u in paso.usos:
            print(f"  → {u.nombre}{'' if u.valida else '  [INVÁLIDA]'}")
            for k, v in u.argumentos.items():
                print(bloque(f"{k}: {v}", "      ", lineas=4))
            print("    devuelve:")
            print(bloque(u.resultado, "      "))
        if not paso.usos:
            print("  → respuesta final, sin pedir herramientas:")
            print(bloque(paso.texto, "      ", lineas=12))
        print()
    print(f"Terminación: {ej.terminacion}")
    incidencias = [f"{i.servicio}/{i.severidad}" for i in p.incidencias] or ["ninguna"]
    print(f"Incidencias en la plataforma: {', '.join(incidencias)}")
    print(f"Comprobación: {plataforma.comprobar(p).motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

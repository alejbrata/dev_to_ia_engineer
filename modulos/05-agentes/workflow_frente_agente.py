"""Workflow frente a agente: la misma tarea, el mismo modelo, las mismas herramientas (lección 01).

En el workflow, el código decide los pasos: dos llamadas al modelo por alerta, siempre.
En el agente, el modelo decide qué herramienta usar y cuándo terminar.

1. Aciertos (estado final de la plataforma), llamadas al modelo, tokens y tiempo.
2. Los escenarios en los que uno acierta y el otro no.

Usa los escenarios de desarrollo. Guarda los resultados en resultados/; con --grabadas los
reutiliza sin llamar al modelo.
Uso: `uv run python modulos/05-agentes/workflow_frente_agente.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median

import agente
import plataforma
import workflow
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar

RESULTADOS = Path(__file__).resolve().parent / "resultados"
ROL = "agente"
OPCIONES_AGENTE = agente.OPCIONES.model_copy(update={"razonar": False})


def con_workflow(cliente: ClienteLLM, indice, escenarios) -> Informe:
    resultados = []
    for e in escenarios:
        p = plataforma.Plataforma(e, indice)
        ej = workflow.ejecutar(cliente, p, rol=ROL)
        c = plataforma.comprobar(p)
        # Un error del workflow es un fallo, aunque deje la plataforma como "no hacía falta".
        ok, motivo = (False, f"error: {ej.error[:80]}") if ej.error else (c.ok, c.motivo)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=ok,
                salida=ej.decision.model_dump_json() if ej.decision else (ej.error or ""),
                detalle={
                    "motivo": motivo,
                    "llamadas_modelo": ej.llamadas_modelo,
                    "herramientas": 3,  # estado, logs y dos búsquedas cuentan como pasos fijos
                    "tokens": ej.tokens,
                    "segundos": round(ej.segundos, 1),
                },
            )
        )
    return Informe(version="workflow", resultados=resultados)


def con_agente(cliente: ClienteLLM, indice, escenarios) -> Informe:
    resultados = []
    for e in escenarios:
        p = plataforma.Plataforma(e, indice)
        ej = agente.ejecutar(cliente, p, rol=ROL, opciones=OPCIONES_AGENTE)
        c = plataforma.comprobar(p)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=c.ok,
                salida=ej.respuesta,
                detalle={
                    "motivo": c.motivo,
                    "llamadas_modelo": len(ej.pasos),
                    "herramientas": len(ej.usos),
                    "tokens": ej.tokens,
                    "segundos": round(ej.segundos, 1),
                    "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos],
                },
            )
        )
    return Informe(version="agente", resultados=resultados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    cliente = None if args.grabadas else ClienteLLM()
    indice = None if args.grabadas else plataforma.indice_documentacion(cliente)

    informes = {}
    for nombre, funcion in [("workflow", con_workflow), ("agente", con_agente)]:
        ruta = RESULTADOS / f"comparacion-{nombre}.jsonl"
        if args.grabadas:
            informes[nombre] = Informe.cargar(ruta)
        else:
            informes[nombre] = funcion(cliente, indice, escenarios)
            informes[nombre].guardar(ruta)

    n = len(escenarios)
    print(f"1. La misma tarea en los {n} escenarios de desarrollo")
    print(
        f"   {'':10} {'estado ok':>9} {'llamadas al modelo':>19} {'tokens':>8} {'s/escenario':>11}"
    )
    for nombre, informe in informes.items():
        rs = informe.resultados
        print(
            f"   {nombre:10} {informe.aciertos:>5} de {n} "
            f"{sum(r.detalle['llamadas_modelo'] for r in rs):>19} "
            f"{sum(r.detalle['tokens'] for r in rs):>8} "
            f"{median(r.detalle['segundos'] for r in rs):>11.0f}"
        )
    print("   (llamadas y tokens: total de los escenarios; segundos: mediana por escenario)")

    c = comparar(informes["workflow"], informes["agente"])
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"\n2. El agente gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    for nombre, informe in informes.items():
        for r in informe.resultados:
            if not r.ok:
                print(f"   {nombre:8} {r.caso}: {r.detalle['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

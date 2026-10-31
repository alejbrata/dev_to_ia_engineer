"""El agente planificador frente al workflow y al agente de la lección 01 (lección 04).

1. Un plan de ejemplo: las tareas, sus dependencias y el orden en que se ejecutan.
2. Las tres arquitecturas en los escenarios de desarrollo: aciertos, llamadas, tokens, tiempo.
3. Cuántas veces hubo que replanificar, y por qué.

Reutiliza los resultados del workflow y del agente de workflow_frente_agente.py. Con
--grabadas no llama al modelo. Uso: `uv run python modulos/05-agentes/planificar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median

import planificador
import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar

RESULTADOS = Path(__file__).resolve().parent / "resultados"
EJEMPLO = "pagos-pool-despliegue"


def ejecutar_todos(cliente: ClienteLLM, escenarios) -> Informe:
    indice = plataforma.indice_documentacion(cliente)
    cliente.descargar_modelo("agente")
    resultados = []
    for e in escenarios:
        p = plataforma.Plataforma(e, indice)
        ej = planificador.ejecutar(cliente, p)
        c = plataforma.comprobar(p)
        ok, motivo = (False, f"error: {ej.error}") if ej.error else (c.ok, c.motivo)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=ok,
                salida=ej.decision.model_dump_json() if ej.decision else (ej.error or ""),
                detalle={
                    "motivo": motivo,
                    "llamadas_modelo": ej.llamadas_modelo,
                    "tokens": ej.tokens,
                    "segundos": round(ej.segundos, 1),
                    "planes": [pl.model_dump() for pl in ej.planes],
                    "errores_de_plan": ej.errores_de_plan,
                    "orden": ej.orden,
                    "resultados": ej.resultados,
                },
            )
        )
    return Informe(version="planificador", resultados=resultados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    ruta = RESULTADOS / "comparacion-planificador.jsonl"
    if args.grabadas:
        plan = Informe.cargar(ruta)
    else:
        plan = ejecutar_todos(ClienteLLM(), escenarios)
        plan.guardar(ruta)
    informes = {
        "workflow": Informe.cargar(RESULTADOS / "comparacion-workflow.jsonl"),
        "agente": Informe.cargar(RESULTADOS / "comparacion-agente.jsonl"),
        "planificador": plan,
    }

    ejemplo = plan.por_caso()[EJEMPLO].detalle
    print(f"1. El plan de {EJEMPLO}")
    for t in ejemplo["planes"][-1]["tareas"]:
        deps = f" ← {', '.join(t['depende_de'])}" if t["depende_de"] else ""
        print(f"   {t['id']}: {t['herramienta']}({t['argumentos']}){deps}")
        print(f"       para qué: {t['para_que']}")
    print(f"   orden de ejecución: {' → '.join(ejemplo['orden'])}")

    n = len(escenarios)
    print(f"\n2. Las tres arquitecturas en los {n} escenarios de desarrollo")
    print(
        f"   {'':13} {'estado ok':>9} {'llamadas al modelo':>19} {'tokens':>8} {'s/escenario':>11}"
    )
    for nombre, informe in informes.items():
        rs = informe.resultados
        print(
            f"   {nombre:13} {informe.aciertos:>5} de {n} "
            f"{sum(r.detalle['llamadas_modelo'] for r in rs):>19} "
            f"{sum(r.detalle['tokens'] for r in rs):>8} "
            f"{median(r.detalle['segundos'] for r in rs):>11.0f}"
        )
    for otro in ["workflow", "agente"]:
        c = comparar(informes[otro], plan)
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        print(f"   frente a {otro}: gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")

    print("\n3. Replanificaciones y fallos del planificador")
    replanes = [
        (r.caso, r.detalle["errores_de_plan"])
        for r in plan.resultados
        if r.detalle["errores_de_plan"]
    ]
    print(f"   escenarios que necesitaron replanificar: {len(replanes)} de {n}")
    for caso, errores in replanes:
        for error in errores:
            print(f"     {caso}: {error[:110]}")
    for r in plan.resultados:
        if not r.ok:
            print(f"   {r.caso}: {r.detalle['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

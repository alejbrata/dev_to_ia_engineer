"""Las mismas herramientas, mejor descritas: versión 1 frente a versión 2 (lección 02).

La versión 2 cambia solo lo que el modelo lee: las descripciones de las herramientas y de
sus argumentos (incluidos los criterios de severidad) y un aviso en abrir_incidencia. El
prompt del agente y los modelos son los mismos.

1. Aciertos, consultas al runbook y llamadas a herramientas con cada versión.
2. Cuántas veces el agente dice que abre la incidencia sin abrirla.
3. Los fallos que quedan con la versión 2.

Reutiliza los resultados de la versión 1 de medir_modelos.py. Con --grabadas no llama al
modelo. Uso: `uv run python modulos/05-agentes/medir_herramientas.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from statistics import median

import medir_modelos
import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, comparar, prueba_mcnemar
from plataforma import corpus

RESULTADOS = Path(__file__).resolve().parent / "resultados"
MODELOS = ["qwen2.5-7b", "qwen3-8b", "qwen3-8b-razonando"]
# "Abro una incidencia", "he abierto la incidencia", "incidencia abierta"...
DICE_QUE_ABRE = re.compile(
    r"\b(abr[oeí]\w*|abiert\w*)\b[^.]{0,60}incidencia|incidencia\w*\s+abiert"
)


def dice_sin_hacer(salida: str, incidencias: list) -> bool:
    """El agente dice que ha abierto una incidencia, pero en la plataforma no hay ninguna."""
    return not incidencias and bool(DICE_QUE_ABRE.search(corpus.normalizar(salida)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    cliente = None if args.grabadas else ClienteLLM()
    indice = None if args.grabadas else plataforma.indice_documentacion(cliente)

    informes: dict[tuple[str, str], Informe] = {}
    for nombre in MODELOS:
        informes[nombre, "v1"] = Informe.cargar(RESULTADOS / f"modelos-{nombre}.jsonl")
        ruta = RESULTADOS / f"herramientas-v2-{nombre}.jsonl"
        if args.grabadas:
            informes[nombre, "v2"] = Informe.cargar(ruta)
        else:
            informes[nombre, "v2"] = medir_modelos.ejecutar(
                cliente, indice, nombre, escenarios, herramientas=plataforma.HERRAMIENTAS
            )
            informes[nombre, "v2"].guardar(ruta)

    n = len(escenarios)
    print(f"1. Herramientas v1 frente a v2, en los {n} escenarios de desarrollo")
    print(
        f"   {'modelo':20} {'versión':>7} {'estado ok':>9} {'runbook':>8} {'llamadas':>9} "
        f"{'inválidas':>9} {'dice sin hacer':>14} {'s/escenario':>11}"
    )
    for (nombre, version), informe in informes.items():
        rs = informe.resultados
        usos = [u for r in rs for u in r.detalle["usos"]]
        sin_hacer = sum(dice_sin_hacer(r.salida, r.detalle["incidencias"]) for r in rs)
        print(
            f"   {nombre:20} {version:>7} {informe.aciertos:>5} de {n} "
            f"{sum(r.detalle['consulto_runbook'] for r in rs):>4} de {n} {len(usos):>9} "
            f"{sum(not u['valida'] for u in usos):>9} {sin_hacer:>14} "
            f"{median(r.detalle['segundos'] for r in rs):>11.0f}"
        )

    print("\n2. v1 → v2, caso a caso")
    for nombre in MODELOS:
        c = comparar(informes[nombre, "v1"], informes[nombre, "v2"])
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        print(f"   {nombre:20} gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")

    print("\n3. Fallos con la versión 2")
    for nombre in MODELOS:
        for r in informes[nombre, "v2"].resultados:
            if not r.ok:
                print(f"   {nombre:20} {r.caso}: {r.detalle['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

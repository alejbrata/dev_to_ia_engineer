"""¿Qué modelo local sirve para el agente? Se mide, no se supone (lección 02).

Ejecuta el agente de guardia en los escenarios de desarrollo con cada configuración y mide
lo que importa en un agente: si deja la plataforma en el estado correcto, si consulta el
runbook antes de decidir, cuántas llamadas a herramientas hace mal, cuántos pasos da y
cuánto tarda. La partición de prueba no se toca: se reserva para la lección 08.

Guarda los resultados en resultados/. Con --grabadas los reutiliza.
Uso: `uv run python modulos/05-agentes/medir_modelos.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median

import agente
import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso

RESULTADOS = Path(__file__).resolve().parent / "resultados"
# nombre: (rol, razonar)
CONFIGURACIONES = {
    "qwen2.5-1.5b": ("chat", None),
    "qwen2.5-7b": ("chat_grande", None),
    "qwen3-8b": ("agente", False),
    "qwen3-8b-razonando": ("agente", True),
}


def ejecutar(
    cliente: ClienteLLM, indice, nombre: str, escenarios, herramientas=plataforma.HERRAMIENTAS_V1
) -> Informe:
    rol, razonar = CONFIGURACIONES[nombre]
    opciones = agente.OPCIONES.model_copy(update={"razonar": razonar})
    cliente.descargar_modelo(rol)
    resultados = []
    for e in escenarios:
        p = plataforma.Plataforma(e, indice)
        # Por defecto, la versión 1 de las herramientas (la v2 se mide en medir_herramientas.py).
        ej = agente.ejecutar(cliente, p, rol=rol, opciones=opciones, herramientas=herramientas)
        c = plataforma.comprobar(p)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=c.ok,
                salida=ej.respuesta,
                detalle={
                    "motivo": c.motivo,
                    "consulto_runbook": c.consulto_runbook,
                    "terminacion": ej.terminacion,
                    "pasos": len(ej.pasos),
                    "tokens": ej.tokens,
                    "segundos": round(ej.segundos, 1),
                    "usos": [u.model_dump() for u in ej.usos],
                    "incidencias": [i.model_dump() for i in p.incidencias],
                },
            )
        )
    return Informe(version=nombre, resultados=resultados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    cliente = None if args.grabadas else ClienteLLM()
    indice = None if args.grabadas else plataforma.indice_documentacion(cliente)

    informes = {}
    for nombre in CONFIGURACIONES:
        ruta = RESULTADOS / f"modelos-{nombre}.jsonl"
        if args.grabadas:
            informes[nombre] = Informe.cargar(ruta)
        else:
            informes[nombre] = ejecutar(cliente, indice, nombre, escenarios)
            informes[nombre].guardar(ruta)

    n = len(escenarios)
    print(f"1. El agente en los {n} escenarios de desarrollo")
    print(
        f"   {'configuración':20} {'estado ok':>9} {'runbook':>8} {'llamadas':>9} "
        f"{'inválidas':>9} {'pasos':>6} {'límite':>7} {'s/escenario':>11}"
    )
    for nombre, informe in informes.items():
        rs = informe.resultados
        usos = [u for r in rs for u in r.detalle["usos"]]
        invalidas = sum(not u["valida"] for u in usos)
        print(
            f"   {nombre:20} {informe.aciertos:>5} de {n} "
            f"{sum(r.detalle['consulto_runbook'] for r in rs):>4} de {n} "
            f"{len(usos):>9} {invalidas:>9} "
            f"{median(r.detalle['pasos'] for r in rs):>6.0f} "
            f"{sum(r.detalle['terminacion'] == 'limite_pasos' for r in rs):>7} "
            f"{median(r.detalle['segundos'] for r in rs):>11.0f}"
        )
    print("   (pasos y segundos: mediana por escenario)")

    print("\n2. Por qué falla cada configuración")
    for nombre, informe in informes.items():
        fallos = [r for r in informe.resultados if not r.ok]
        print(f"   {nombre}: {len(fallos)} fallos")
        for r in fallos:
            print(f"     {r.caso}: {r.detalle['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

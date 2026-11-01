"""Evals de agentes: resultado, trayectoria, fiabilidad y coste (lección 12).

El agente de la lección 03 y el grafo de la lección 05, cuatro veces cada uno sobre los 5
escenarios de prueba, que el módulo ha reservado hasta ahora.

Dos formas de repetir: cuatro veces seguidas, igual (repetido), y cada vez con el modelo
recién cargado y la alerta redactada de otra forma (variado, `datos/alertas_variantes.json`).

1. Resultado: aciertos por intento, pass@k (acierta alguna vez) y pass^k (acierta siempre).
2. Escenario a escenario: cuántas de las 4 veces acierta cada sistema.
3. Trayectoria del agente: qué hizo por el camino, no solo cómo acabó.
4. Coste: tokens y tiempo por intento, y por tarea resuelta.

Con --grabadas no llama al modelo. Uso: `uv run python modulos/05-agentes/evals_agentes.py`
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from statistics import mean, median

import agente
import grafos
import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, pass_at_k, pass_hat_k
from medir_herramientas import DICE_QUE_ABRE

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
DATOS = AQUI / "datos"
ROL = "agente"
OPCIONES = agente.OPCIONES.model_copy(update={"razonar": False})
INTENTOS = 4
SISTEMAS = ["agente", "grafo"]
MODOS = ["repetido", "variado"]
SUFIJO = {"repetido": "", "variado": "-variado"}


def con_agente(cliente, indice, escenario, intento: int) -> ResultadoCaso:
    p = plataforma.Plataforma(escenario, indice)
    ej = agente.ejecutar(cliente, p, rol=ROL, opciones=OPCIONES)
    c = plataforma.comprobar(p)
    return ResultadoCaso(
        caso=f"{escenario.id}#{intento}",
        ok=c.ok,
        salida=ej.respuesta,
        detalle={
            "motivo": c.motivo,
            "consulto_runbook": c.consulto_runbook,
            "pasos": len(ej.pasos),
            "terminacion": ej.terminacion,
            "tokens": ej.tokens,
            "segundos": round(ej.segundos, 1),
            "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos],
            "invalidas": sum(not u.valida for u in ej.usos),
            "incidencias": len(p.incidencias),
        },
    )


def con_grafo(cliente, indice, escenario, intento: int) -> ResultadoCaso:
    s = grafos.resolver(cliente, indice, escenario, lambda _: {"aprobada": True})
    return ResultadoCaso(
        caso=f"{escenario.id}#{intento}",
        ok=s["ok"],
        salida="",
        detalle={
            "motivo": s["motivo"],
            "tokens": s["tokens"],
            "segundos": s["segundos"],
            "llamadas_modelo": s["llamadas_modelo"],
        },
    )


def trayectoria(r: ResultadoCaso) -> dict[str, bool]:
    """Comprobaciones sobre lo que hizo el agente por el camino."""
    nombres = [u.split("(", 1)[0] for u in r.detalle["usos"]]
    abrir = nombres.index("abrir_incidencia") if "abrir_incidencia" in nombres else len(nombres)
    antes = nombres[:abrir]
    llamadas = [
        (u.split("(", 1)[0], ast.literal_eval(u.split("(", 1)[1][:-1])) for u in r.detalle["usos"]
    ]
    repetidas = len(llamadas) != len({(n, tuple(sorted(a.items()))) for n, a in llamadas})
    return {
        "miró el estado antes de decidir": "estado_servicio" in antes,
        "miró los logs antes de decidir": "buscar_logs" in antes,
        "consultó el runbook del problema": r.detalle["consulto_runbook"],
        "sin llamadas inválidas": r.detalle["invalidas"] == 0,
        "sin llamadas repetidas": not repetidas,
        "no dice que abre sin abrir": not (
            r.detalle["incidencias"] == 0
            and DICE_QUE_ABRE.search(plataforma.corpus.normalizar(r.salida))
        ),
        "terminó antes del límite de pasos": r.detalle["terminacion"] == "respuesta",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    parser.add_argument(
        "--solo-variado", action="store_true", help="repite solo la medición variada"
    )
    agente.argumento_rol(parser)
    args = parser.parse_args()
    resultados = agente.usar_rol(args.rol, RESULTADOS)
    escenarios = [e for e in plataforma.cargar() if e.particion == "prueba"]
    variantes = json.loads((DATOS / "alertas_variantes.json").read_text(encoding="utf-8"))
    rutas = {(s, m): resultados / f"evals-{s}{SUFIJO[m]}.jsonl" for s in SISTEMAS for m in MODOS}

    if args.grabadas:
        informes = {clave: Informe.cargar(r) for clave, r in rutas.items()}
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        modos = ["variado"] if args.solo_variado else MODOS
        informes = {clave: Informe.cargar(r) for clave, r in rutas.items() if clave[1] not in modos}
        for m in modos:
            for s, funcion in [("agente", con_agente), ("grafo", con_grafo)]:
                rs = []
                cliente.descargar_modelo(ROL)
                for i in range(1, INTENTOS + 1):
                    for e in escenarios:
                        if m == "variado":
                            # Cada intento en frío y, salvo el primero, con la alerta reescrita.
                            cliente.descargar_modelo(ROL)
                            if i > 1:
                                e = e.model_copy(update={"alerta": variantes[e.id][i - 2]})
                        rs.append(funcion(cliente, indice, e, i))
                informes[s, m] = Informe(version=f"{s}-{m}", resultados=rs)
                informes[s, m].guardar(rutas[s, m])

    def aciertos_por_escenario(inf: Informe) -> dict[str, int]:
        cuenta = {e.id: 0 for e in escenarios}
        for r in inf.resultados:
            cuenta[r.caso.split("#")[0]] += r.ok
        return cuenta

    n, k = len(escenarios), INTENTOS
    print(f"1. Resultado en los {n} escenarios de prueba, {k} intentos cada uno")
    print("   repetido: el mismo escenario 4 veces seguidas, con el modelo ya cargado")
    print(
        "   variado: cada intento con el modelo recién cargado y, del 2 al 4, la alerta reescrita"
    )
    print(
        f"   {'':18} {'aciertos':>9} "
        + " ".join(f"{f'pass^{j}':>7}" for j in range(1, k + 1))
        + f" {'pass@4':>7}"
    )
    for (s, m), inf in informes.items():
        c = aciertos_por_escenario(inf)
        hat = [mean(pass_hat_k(x, k, j) for x in c.values()) for j in range(1, k + 1)]
        at = mean(pass_at_k(x, k, k) for x in c.values())
        print(
            f"   {f'{s}, {m}':18} {inf.aciertos:>3} de {len(inf.resultados)} "
            + " ".join(f"{h:>7.2f}" for h in hat)
            + f" {at:>7.2f}"
        )

    print(f"\n2. Aciertos de cada escenario en los {k} intentos")
    cuentas = {clave: aciertos_por_escenario(inf) for clave, inf in informes.items()}
    claves = list(informes)
    print(f"   {'escenario':30} " + " ".join(f"{f'{s[:6]}/{m[:3]}':>11}" for s, m in claves))
    for e in escenarios:
        print(f"   {e.id:30} " + " ".join(f"{cuentas[c][e.id]:>9}/{k}" for c in claves))
    variado = informes["agente", "variado"]
    print("   fallos del agente, variado (intento 1: alerta original; 2 a 4: reescrita)")
    for r in sorted(variado.resultados, key=lambda r: r.caso):
        if not r.ok:
            print(f"     {r.caso:34} {r.detalle['motivo']}")

    print("\n3. Trayectoria del agente, variado (en cuántos de los intentos se cumple)")
    rs = variado.resultados
    tray = [trayectoria(r) for r in rs]
    for comprobacion in tray[0]:
        total = sum(t[comprobacion] for t in tray)
        print(f"   {comprobacion:36} {total:>3} de {len(tray)}")
    for m in MODOS:
        rm = informes["agente", m].resultados
        distintas = [
            len(
                {
                    tuple(u.split("(", 1)[0] for u in r.detalle["usos"])
                    for r in rm
                    if r.caso.startswith(e.id + "#")
                }
            )
            for e in escenarios
        ]
        print(f"   secuencias de herramientas distintas por escenario, {m}: {distintas}")
    print(f"   pasos por intento, variado: mediana {median(r.detalle['pasos'] for r in rs):.0f}")

    print("\n4. Coste (variado)")
    print(f"   {'':8} {'tokens/intento':>15} {'s/intento':>10} {'tokens por tarea resuelta':>26}")
    for s in SISTEMAS:
        inf = informes[s, "variado"]
        tokens = [r.detalle["tokens"] for r in inf.resultados]
        resueltas = inf.aciertos
        por_tarea = f"{sum(tokens) / resueltas:>26.0f}" if resueltas else f"{'∞':>26}"
        print(
            f"   {s:8} {mean(tokens):>15.0f} "
            f"{median(r.detalle['segundos'] for r in inf.resultados):>10.0f} {por_tarea}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

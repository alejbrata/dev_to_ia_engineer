"""Subagentes frente al agente único, en el agente de guardia (lección 08).

1. Un escenario: qué delega el orquestador, a quién, y qué le vuelve.
2. Los escenarios de desarrollo: aciertos, tokens del contexto principal y totales, tiempo.
3. ¿Ahorra tiempo delegar en paralelo? Tres peticiones iguales, en serie y a la vez.
4. Los fallos que quedan.

El agente único es el de memoria_y_contexto.py (sin memoria). Con --grabadas no llama al
modelo. Uso: `uv run python modulos/05-agentes/delegar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

import plataforma
import subagentes
from curso_core import ClienteLLM, Opciones
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar

RESULTADOS = Path(__file__).resolve().parent / "resultados"
ROL = "agente"
OPCIONES = Opciones(temperatura=0, max_tokens=800, razonar=False)
EJEMPLO = "pagos-pool-despliegue"
PRUEBA_PARALELO = "Resume en una frase qué es un pool de conexiones."


def con_subagentes(cliente, indice, escenarios) -> Informe:
    resultados = []
    for e in escenarios:
        p = plataforma.Plataforma(e, indice)
        ej = subagentes.ejecutar(cliente, p, rol=ROL, opciones=OPCIONES)
        c = plataforma.comprobar(p)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=c.ok,
                salida=ej.orquestador.respuesta,
                detalle={
                    "motivo": c.motivo,
                    "pasos": len(ej.orquestador.pasos),
                    "tokens": ej.tokens,
                    "tokens_principal": ej.orquestador.tokens,
                    "entrada_por_paso": [x.tokens_entrada for x in ej.orquestador.pasos],
                    "segundos": round(ej.segundos, 1),
                    "terminacion": ej.orquestador.terminacion,
                    "delegaciones": [d.model_dump() for d in ej.delegaciones],
                    "usos": [f"{u.nombre}({u.argumentos})" for u in ej.orquestador.usos],
                },
            )
        )
    return Informe(version="subagentes", resultados=resultados)


def medir_paralelo(cliente: ClienteLLM, n: int = 3) -> dict:
    def pedir(_):
        return cliente.chat(PRUEBA_PARALELO, rol=ROL, opciones=OPCIONES)

    pedir(0)  # el modelo ya cargado, para que la carga no cuente en ninguna de las dos
    inicio = time.perf_counter()
    for i in range(n):
        pedir(i)
    serie = time.perf_counter() - inicio
    inicio = time.perf_counter()
    with ThreadPoolExecutor(n) as pool:
        list(pool.map(pedir, range(n)))
    return {"n": n, "serie": round(serie, 1), "paralelo": round(time.perf_counter() - inicio, 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    ruta, ruta_paralelo = RESULTADOS / "subagentes.jsonl", RESULTADOS / "subagentes-paralelo.json"

    if args.grabadas:
        sub = Informe.cargar(ruta)
        paralelo = json.loads(ruta_paralelo.read_text(encoding="utf-8"))
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        cliente.descargar_modelo(ROL)
        sub = con_subagentes(cliente, indice, escenarios)
        sub.guardar(ruta)
        paralelo = medir_paralelo(cliente)
        ruta_paralelo.write_text(json.dumps(paralelo), encoding="utf-8")

    ids = {e.id for e in escenarios}
    completo = Informe.cargar(RESULTADOS / "memoria-completo.jsonl")
    unico = Informe(version="agente", resultados=[r for r in completo.resultados if r.caso in ids])

    d = sub.por_caso()[EJEMPLO].detalle
    print(f"1. {EJEMPLO}: lo que delega el orquestador")
    for x in d["delegaciones"]:
        print(
            f"   {x['subagente']:23} {x['pasos']} pasos {x['tokens']:>6} tokens "
            f"{x['segundos']:5.0f} s  {x['tarea'][:60]}"
        )
        print(f"      informe: {x['respuesta'][:150]!r}")
    print(f"   orquestador: {d['pasos']} pasos, {d['tokens_principal']} tokens → {d['motivo']}")

    n = len(escenarios)
    print(f"\n2. Los {n} escenarios de desarrollo")
    print(
        f"   {'':11} {'estado ok':>9} {'tokens principal':>17} {'tokens total':>13} "
        f"{'entrada máx.':>13} {'s/escenario':>11}"
    )
    for nombre, inf, clave in [
        ("agente", unico, "tokens"),
        ("subagentes", sub, "tokens_principal"),
    ]:
        rs = inf.resultados
        print(
            f"   {nombre:11} {inf.aciertos:>5} de {n} "
            f"{sum(r.detalle[clave] for r in rs):>17} "
            f"{sum(r.detalle['tokens'] for r in rs):>13} "
            f"{max(max(r.detalle['entrada_por_paso']) for r in rs):>13} "
            f"{median(r.detalle['segundos'] for r in rs):>11.0f}"
        )
    c = comparar(unico, sub)
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   subagentes gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    delegaciones = [x for r in sub.resultados for x in r.detalle["delegaciones"]]
    por_tipo = {s: sum(x["subagente"] == s for x in delegaciones) for s in subagentes.SUBAGENTES}
    sin_informe = sum(x["terminacion"] != "respuesta" for x in delegaciones)
    print(f"   delegaciones: {len(delegaciones)} {por_tipo}; sin informe: {sin_informe}")

    print(f"\n3. {paralelo['n']} peticiones iguales al mismo modelo local")
    print(f"   en serie: {paralelo['serie']} s; a la vez: {paralelo['paralelo']} s")

    print("\n4. Fallos con subagentes")
    for r in sub.resultados:
        if not r.ok:
            print(f"   {r.caso}: {r.detalle['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

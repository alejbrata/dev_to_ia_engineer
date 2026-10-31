"""El agente de guardia como grafo de estado, con un motor propio (lección 05).

1. El grafo: nodos y aristas.
2. Un escenario paso a paso: el grafo se para antes de abrir la incidencia, una persona la
   aprueba y el grafo se reanuda desde el checkpoint.
3. Una caída a mitad: el proceso falla en `decidir` y se reanuda sin repetir lo hecho.
4. Los escenarios de desarrollo, aprobando todo, frente al workflow de la lección 01.

Con --humano, la aprobación la haces tú en la terminal. Con --grabadas, no llama al modelo.
Uso: `uv run python modulos/05-agentes/grafos.py [--grabadas | --humano]`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar
from grafo import Checkpoints
from grafo_guardia import EstadoGuardia, NodosGuardia, construir

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
CHECKPOINTS = Checkpoints(AQUI / "checkpoints")
EJEMPLO = "pagos-pool-despliegue"
CAIDA = "usuarios-deadlocks"
APROBACION = frozenset({"abrir"})


def aprobar_en_terminal(estado: EstadoGuardia) -> dict:
    d = estado.decision
    print(f"\n   Propuesta: {estado.servicio}, severidad {d.severidad}")
    print(f"   Resumen: {d.resumen}\n   Mitigación: {d.mitigacion}")
    respuesta = input("   ¿Abrir? [s]í / [n]o / o escribe otra severidad: ").strip().lower()
    if respuesta in {"critica", "alta", "media", "baja"}:
        return {"aprobada": True, "decision": d.model_copy(update={"severidad": respuesta})}
    return {"aprobada": respuesta in {"", "s", "si", "sí"}}


def resolver(cliente, indice, escenario, aprobar) -> dict:
    """Ejecuta un escenario hasta el final, pasando por la aprobación si el grafo se para."""
    p = plataforma.Plataforma(escenario, indice)
    grafo = construir(NodosGuardia(cliente, p))
    hilo = escenario.id
    primera = grafo.ejecutar(
        EstadoGuardia(alerta=escenario.alerta),
        hilo=hilo,
        checkpoints=CHECKPOINTS,
        interrumpir_antes=APROBACION,
    )
    salida = {"pasos": [x.model_dump() for x in primera.pasos], "pendiente": primera.pendiente}
    final = primera
    if primera.pendiente:
        salida["checkpoints"] = len(CHECKPOINTS.ruta(hilo).read_text().splitlines())
        salida["propuesta"] = primera.estado.decision.model_dump()
        cambios = aprobar(primera.estado)
        final = grafo.ejecutar(
            None, hilo=hilo, checkpoints=CHECKPOINTS, interrumpir_antes=APROBACION, cambios=cambios
        )
        salida["cambios"] = {
            k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in cambios.items()
        }
        salida["pasos_reanudacion"] = [x.model_dump() for x in final.pasos]
    pasos = primera.pasos + (final.pasos if final is not primera else [])
    e = final.estado
    c = plataforma.comprobar(p)
    ok, motivo = (False, f"error: {e.error[:80]}") if e.error else (c.ok, c.motivo)
    salida.update(
        ok=ok,
        motivo=motivo,
        llamadas_modelo=e.llamadas_modelo,
        tokens=e.tokens,
        segundos=round(sum(x.segundos for x in pasos), 1),
        incidencia=e.incidencia,
        intentos=e.intentos,
    )
    return salida


class Caida(Exception):
    pass


def con_caida(cliente, indice, escenario) -> dict:
    """Ejecuta un escenario, hace que `decidir` falle la primera vez y reanuda."""
    p = plataforma.Plataforma(escenario, indice)
    nodos = NodosGuardia(cliente, p)
    grafo = construir(nodos)
    decidir, fallos = nodos.decidir, []

    def decidir_que_cae(estado):
        if not fallos:
            fallos.append(1)
            raise Caida("el proceso muere a mitad de decidir")
        return decidir(estado)

    grafo.nodo("decidir", decidir_que_cae)
    salida = {}
    try:
        grafo.ejecutar(
            EstadoGuardia(alerta=escenario.alerta), hilo="caida", checkpoints=CHECKPOINTS
        )
    except Caida as error:
        salida["error"] = str(error)
    ultimo = CHECKPOINTS.ultimo("caida")
    salida["checkpoint"] = {
        "siguiente": ultimo["siguiente"],
        "llamadas_modelo": ultimo["estado"]["llamadas_modelo"],
        "tokens": ultimo["estado"]["tokens"],
        "servicio": ultimo["estado"]["servicio"],
    }
    final = grafo.ejecutar(None, hilo="caida", checkpoints=CHECKPOINTS)
    salida["pasos_reanudacion"] = [x.nodo for x in final.pasos]
    salida["llamadas_modelo"] = final.estado.llamadas_modelo
    salida["ok"] = plataforma.comprobar(p).ok
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    modo.add_argument("--humano", action="store_true", help="apruebas tú cada incidencia")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    ruta, ruta_caida = RESULTADOS / "grafo.jsonl", RESULTADOS / "grafo-caida.json"

    if args.grabadas:
        informe = Informe.cargar(ruta)
        caida = json.loads(ruta_caida.read_text(encoding="utf-8"))
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        cliente.descargar_modelo("agente")
        aprobar = aprobar_en_terminal if args.humano else (lambda _: {"aprobada": True})
        resultados = []
        for e in escenarios:
            s = resolver(cliente, indice, e, aprobar)
            resultados.append(ResultadoCaso(caso=e.id, ok=s["ok"], salida="", detalle=s))
        informe = Informe(version="grafo", resultados=resultados)
        caida = con_caida(cliente, indice, next(e for e in escenarios if e.id == CAIDA))
        if not args.humano:
            informe.guardar(ruta)
            ruta_caida.write_text(json.dumps(caida, ensure_ascii=False, indent=2), "utf-8")

    grafo = construir(NodosGuardia(None, None))
    print("1. El grafo")
    for origen, destinos in grafo.destinos.items():
        tipo = "condicional" if len(destinos) > 1 else "fija"
        print(f"   {origen:10} → {' | '.join(sorted(destinos)):24} ({tipo})")
    print(f"   parada para aprobación antes de: {', '.join(APROBACION)}")

    d = informe.por_caso()[EJEMPLO].detalle
    print(f"\n2. {EJEMPLO}, paso a paso")
    for x in d["pasos"]:
        print(f"   {x['nodo']:10} {x['segundos']:5.1f} s")
    print(f"   ⏸ parado antes de {d['pendiente']!r}; checkpoints guardados: {d['checkpoints']}")
    pr = d["propuesta"]
    print(f"   propuesta: abrir={pr['abrir']}, severidad={pr['severidad']}")
    print(f"   mitigación: {pr['mitigacion'][:90]}")
    print(f"   la persona decide: {d['cambios']}")
    for x in d["pasos_reanudacion"]:
        print(f"   ▶ {x['nodo']:8} {x['segundos']:5.1f} s")
    print(f"   resultado: {d['incidencia']} → {d['motivo']}")

    print(f"\n3. Caída a mitad de {CAIDA}")
    print(f"   error: {caida['error']}")
    ck = caida["checkpoint"]
    print(
        f"   último checkpoint: siguiente={ck['siguiente']!r}, servicio={ck['servicio']}, "
        f"llamadas ya hechas={ck['llamadas_modelo']}, tokens={ck['tokens']}"
    )
    print(f"   al reanudar se ejecutan: {' → '.join(caida['pasos_reanudacion'])}")
    print(f"   llamadas al modelo en total: {caida['llamadas_modelo']}; estado ok: {caida['ok']}")

    n = len(escenarios)
    rs = informe.resultados
    workflow = Informe.cargar(RESULTADOS / "comparacion-workflow.jsonl")
    print(f"\n4. Los {n} escenarios de desarrollo, aprobando todo")
    print(
        f"   {'':9} {'estado ok':>9} {'llamadas al modelo':>19} {'tokens':>8} {'s/escenario':>11}"
    )
    for nombre, inf in [("workflow", workflow), ("grafo", informe)]:
        print(
            f"   {nombre:9} {inf.aciertos:>5} de {n} "
            f"{sum(r.detalle['llamadas_modelo'] for r in inf.resultados):>19} "
            f"{sum(r.detalle['tokens'] for r in inf.resultados):>8} "
            f"{median(r.detalle['segundos'] for r in inf.resultados):>11.0f}"
        )
    print("   (los segundos del workflow son de otra ejecución: compara llamadas y tokens)")
    c = comparar(workflow, informe)
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   frente al workflow: gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    paradas = [r for r in rs if r.detalle["pendiente"]]
    reintentos = sum(r.detalle["intentos"] - 1 for r in rs)
    print(f"   paradas para aprobación: {len(paradas)}; repeticiones de decidir: {reintentos}")
    for r in rs:
        if not r.ok:
            visto = "la persona lo ve" if r.detalle["pendiente"] else "no llega a la persona"
            print(f"   {r.caso}: {r.detalle['motivo']} ({visto})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

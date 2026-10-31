"""El mismo grafo de guardia con LangGraph, frente al motor propio (lección 06).

1. El grafo, tal como lo ve LangGraph.
2. Un escenario paso a paso: `interrupt()` para el grafo y `Command(resume=...)` lo reanuda.
3. Una caída a mitad de `decidir` y la reanudación desde el checkpoint de SQLite.
4. Los escenarios de desarrollo, aprobando todo, frente al motor propio de la lección 05.
5. Lo que cuesta cada motor por paso, con nodos que no hacen nada.

Con --grabadas, no llama al modelo (la parte 5 sí se ejecuta: no usa modelo).
Uso: `uv run python modulos/05-agentes/con_langgraph.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from statistics import median

import grafo_langgraph
import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar
from grafo import FIN, Checkpoints, Grafo
from grafo_guardia import EstadoGuardia, NodosGuardia
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
CHECKPOINTS = AQUI / "checkpoints"
EJEMPLO = "pagos-pool-despliegue"
CAIDA = "usuarios-deadlocks"
PASOS_MOTOR = 200


def checkpointer(nombre: str) -> SqliteSaver:
    CHECKPOINTS.mkdir(exist_ok=True)
    ruta = CHECKPOINTS / f"{nombre}.db"
    ruta.unlink(missing_ok=True)
    # Los tipos propios que se guardan en el estado se declaran: al leer un checkpoint,
    # LangGraph solo reconstruye los tipos de esta lista (anatomía de la lección).
    serde = JsonPlusSerializer(allowed_msgpack_modules=[("workflow", "Decision")])
    return SqliteSaver(sqlite3.connect(ruta, check_same_thread=False), serde=serde)


def recorrer(grafo, entrada, config) -> tuple[list[dict], dict | None]:
    """Ejecuta hasta el final o hasta una interrupción. Devuelve los nodos con su tiempo y,
    si se ha parado, lo que `interrupt()` enseña a la persona."""
    pasos, inicio = [], time.perf_counter()
    for actualizacion in grafo.stream(entrada, config, stream_mode="updates"):
        for nodo, valor in actualizacion.items():
            if nodo == "__interrupt__":
                return pasos, valor[0].value
            pasos.append({"nodo": nodo, "segundos": round(time.perf_counter() - inicio, 1)})
            inicio = time.perf_counter()
    return pasos, None


def resolver(cliente, indice, escenario, guardar) -> dict:
    p = plataforma.Plataforma(escenario, indice)
    grafo = grafo_langgraph.construir(NodosGuardia(cliente, p), guardar)
    config = {"configurable": {"thread_id": escenario.id}}
    pasos, pendiente = recorrer(grafo, EstadoGuardia(alerta=escenario.alerta), config)
    salida = {"pasos": pasos, "pendiente": pendiente is not None}
    reanudacion = []
    if pendiente is not None:
        salida["propuesta"] = pendiente["decision"]
        salida["siguiente"] = list(grafo.get_state(config).next)
        reanudacion, _ = recorrer(grafo, Command(resume={"aprobada": True}), config)
        salida["pasos_reanudacion"] = reanudacion
    valores = grafo.get_state(config).values
    e = EstadoGuardia.model_validate(valores)
    c = plataforma.comprobar(p)
    ok, motivo = (False, f"error: {e.error[:80]}") if e.error else (c.ok, c.motivo)
    salida.update(
        ok=ok,
        motivo=motivo,
        llamadas_modelo=e.llamadas_modelo,
        tokens=e.tokens,
        segundos=round(sum(x["segundos"] for x in pasos + reanudacion), 1),
        incidencia=e.incidencia,
        tipo_valores=type(valores).__name__,
    )
    return salida


class Caida(Exception):
    pass


def con_caida(cliente, indice, escenario, guardar) -> dict:
    p = plataforma.Plataforma(escenario, indice)
    nodos = NodosGuardia(cliente, p)
    decidir, fallos = nodos.decidir, []

    def decidir_que_cae(estado):
        if not fallos:
            fallos.append(1)
            raise Caida("el proceso muere a mitad de decidir")
        return decidir(estado)

    nodos.decidir = decidir_que_cae
    grafo = grafo_langgraph.construir(nodos, guardar)
    config = {"configurable": {"thread_id": "caida"}}
    salida = {}
    try:
        recorrer(grafo, EstadoGuardia(alerta=escenario.alerta), config)
    except Caida as error:
        salida["error"] = str(error)
    estado = grafo.get_state(config)
    salida["siguiente"] = list(estado.next)
    salida["llamadas_hechas"] = estado.values["llamadas_modelo"]
    pasos, pendiente = recorrer(grafo, None, config)
    if pendiente is not None:
        mas, _ = recorrer(grafo, Command(resume={"aprobada": True}), config)
        pasos += mas
    salida["pasos_reanudacion"] = [x["nodo"] for x in pasos]
    salida["llamadas_modelo"] = grafo.get_state(config).values["llamadas_modelo"]
    salida["ok"] = plataforma.comprobar(p).ok
    return salida


class Contador(BaseModel):
    n: int = 0


def coste_por_paso() -> dict[str, float]:
    """Milisegundos por paso de cada motor, con un nodo que solo suma 1."""

    def sumar(e: Contador) -> dict:
        return {"n": e.n + 1}

    def seguir(e: Contador) -> str:
        return "sumar" if e.n < PASOS_MOTOR else FIN

    propio = Grafo(Contador, inicio="sumar")
    propio.nodo("sumar", sumar)
    propio.arista_condicional("sumar", seguir, {"sumar", FIN})
    inicio = time.perf_counter()
    propio.ejecutar(
        Contador(), hilo="contador", checkpoints=Checkpoints(CHECKPOINTS), max_pasos=PASOS_MOTOR
    )
    ms_propio = (time.perf_counter() - inicio) * 1000 / PASOS_MOTOR

    g = StateGraph(Contador)
    g.add_node("sumar", sumar)
    g.add_edge(START, "sumar")
    g.add_conditional_edges("sumar", seguir, {"sumar": "sumar", FIN: END})
    lg = g.compile(checkpointer=checkpointer("contador"))
    inicio = time.perf_counter()
    lg.invoke(
        Contador(),
        {"configurable": {"thread_id": "contador"}, "recursion_limit": PASOS_MOTOR + 1},
    )
    ms_langgraph = (time.perf_counter() - inicio) * 1000 / PASOS_MOTOR
    return {"motor propio (JSONL)": ms_propio, "LangGraph (SQLite)": ms_langgraph}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    ruta, ruta_caida = RESULTADOS / "langgraph.jsonl", RESULTADOS / "langgraph-caida.json"

    if args.grabadas:
        informe = Informe.cargar(ruta)
        caida = json.loads(ruta_caida.read_text(encoding="utf-8"))
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        cliente.descargar_modelo("agente")
        guardar = checkpointer("guardia")
        resultados = []
        for e in escenarios:
            s = resolver(cliente, indice, e, guardar)
            resultados.append(ResultadoCaso(caso=e.id, ok=s["ok"], salida="", detalle=s))
        informe = Informe(version="langgraph", resultados=resultados)
        informe.guardar(ruta)
        escenario = next(e for e in escenarios if e.id == CAIDA)
        caida = con_caida(cliente, indice, escenario, checkpointer("caida"))
        ruta_caida.write_text(json.dumps(caida, ensure_ascii=False, indent=2), "utf-8")

    grafo = grafo_langgraph.construir(NodosGuardia(None, None), None)
    print("1. El grafo, según LangGraph")
    for arista in grafo.get_graph().edges:
        tipo = " (condicional)" if arista.conditional else ""
        print(f"   {arista.source:10} → {arista.target}{tipo}")

    d = informe.por_caso()[EJEMPLO].detalle
    print(f"\n2. {EJEMPLO}, paso a paso")
    for x in d["pasos"]:
        print(f"   {x['nodo']:10} {x['segundos']:5.1f} s")
    pr = d["propuesta"]
    print(f"   ⏸ interrupt() en 'aprobar'; siguiente según el checkpoint: {d['siguiente']}")
    print(f"   propuesta: abrir={pr['abrir']}, severidad={pr['severidad']}")
    print("   la persona responde: Command(resume={'aprobada': True})")
    for x in d["pasos_reanudacion"]:
        print(f"   ▶ {x['nodo']:8} {x['segundos']:5.1f} s")
    print(f"   resultado: {d['incidencia']} → {d['motivo']}")
    print(f"   get_state(...).values es un {d['tipo_valores']}, no un EstadoGuardia")

    print(f"\n3. Caída a mitad de {CAIDA}")
    print(f"   error: {caida['error']}")
    print(
        f"   get_state(...).next = {caida['siguiente']}; "
        f"llamadas ya hechas = {caida['llamadas_hechas']}"
    )
    print(f"   al reanudar se ejecutan: {' → '.join(caida['pasos_reanudacion'])}")
    print(f"   llamadas al modelo en total: {caida['llamadas_modelo']}; estado ok: {caida['ok']}")

    n = len(escenarios)
    propio = Informe.cargar(RESULTADOS / "grafo.jsonl")
    print(f"\n4. Los {n} escenarios de desarrollo, aprobando todo")
    print(
        f"   {'':12} {'estado ok':>9} {'llamadas al modelo':>19} {'tokens':>8} {'s/escenario':>11}"
    )
    for nombre, inf in [("motor propio", propio), ("LangGraph", informe)]:
        print(
            f"   {nombre:12} {inf.aciertos:>5} de {n} "
            f"{sum(r.detalle['llamadas_modelo'] for r in inf.resultados):>19} "
            f"{sum(r.detalle['tokens'] for r in inf.resultados):>8} "
            f"{median(r.detalle['segundos'] for r in inf.resultados):>11.0f}"
        )
    c = comparar(propio, informe)
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   LangGraph gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    for r in informe.resultados:
        if not r.ok:
            print(f"   {r.caso}: {r.detalle['motivo']}")

    print(f"\n5. Coste del motor por paso ({PASOS_MOTOR} pasos de un nodo que solo suma 1)")
    for nombre, ms in coste_por_paso().items():
        print(f"   {nombre:21} {ms:6.2f} ms/paso")
    print("   (varía de una ejecución a otra; lo que importa es el orden de magnitud)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

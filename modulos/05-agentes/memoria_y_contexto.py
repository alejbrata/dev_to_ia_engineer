"""Contexto y memoria del agente de guardia (lección 07).

1. Cómo crece el contexto en cada paso del bucle.
2. Recortar los resultados antiguos de herramientas: tokens frente a aciertos.
3. Memoria de notas de escenarios ya cerrados, dejando fuera cada vez el propio escenario.
4. Qué notas recupera la memoria en un caso, y los fallos que quedan.

El agente sin cambios se ejecuta en los 14 escenarios; el recorte, en los 9 de desarrollo;
la memoria, en los 14. Con --grabadas no llama al modelo.
Uso: `uv run python modulos/05-agentes/memoria_y_contexto.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median

import agente
import corpus
import memoria
import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar
from medir_herramientas import DICE_QUE_ABRE

RESULTADOS = Path(__file__).resolve().parent / "resultados"
ROL = "agente"
OPCIONES = agente.OPCIONES.model_copy(update={"razonar": False})
EJEMPLO = "pagos-pool-sin-despliegue"


def ejecutar_todos(cliente, indice, escenarios, version, configurar) -> Informe:
    resultados = []
    for e in escenarios:
        p = plataforma.Plataforma(e, indice)
        argumentos, extra = configurar(e)
        ej = agente.ejecutar(cliente, p, rol=ROL, opciones=OPCIONES, **argumentos)
        c = plataforma.comprobar(p)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=c.ok,
                salida=ej.respuesta,
                detalle={
                    "motivo": c.motivo,
                    "pasos": len(ej.pasos),
                    "tokens": ej.tokens,
                    "entrada_por_paso": [x.tokens_entrada for x in ej.pasos],
                    "segundos": round(ej.segundos, 1),
                    "terminacion": ej.terminacion,
                    "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos],
                    **extra,
                },
            )
        )
    return Informe(version=version, resultados=resultados)


def severidad_mal(r: ResultadoCaso) -> bool:
    return "severidad" in r.detalle["motivo"]


def dice_sin_hacer(r: ResultadoCaso) -> bool:
    """Dice en su respuesta que abre la incidencia, pero no llamó a abrir_incidencia."""
    no_abrio = r.detalle["motivo"] == "no abrió la incidencia"
    return no_abrio and bool(DICE_QUE_ABRE.search(corpus.normalizar(r.salida)))


def fila(nombre: str, inf: Informe, n: int) -> str:
    rs = inf.resultados
    return (
        f"   {nombre:11} {inf.aciertos:>5} de {n:<2} {sum(r.detalle['pasos'] for r in rs):>6} "
        f"{sum(r.detalle['tokens'] for r in rs):>8} "
        f"{max(max(r.detalle['entrada_por_paso']) for r in rs):>13} "
        f"{median(r.detalle['segundos'] for r in rs):>11.0f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    todos = plataforma.cargar()
    desarrollo = [e for e in todos if e.particion == "desarrollo"]
    rutas = {v: RESULTADOS / f"memoria-{v}.jsonl" for v in ["completo", "recortado", "memoria"]}

    if args.grabadas:
        informes = {v: Informe.cargar(r) for v, r in rutas.items()}
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        mem = memoria.Memoria(cliente, todos)
        cliente.descargar_modelo(ROL)

        def con_memoria(e):
            notas = mem.buscar(e.alerta, excluir=e.id)
            variables = {"alerta": e.alerta, "memoria": memoria.como_texto(notas)}
            return {"prompt": "agentes/guardia-memoria", "variables": variables}, {
                "notas": [n.doc for n in notas]
            }

        configuraciones = {
            "completo": (todos, lambda e: ({}, {})),
            "recortado": (desarrollo, lambda e: ({"contexto": memoria.recortar()}, {})),
            "memoria": (todos, con_memoria),
        }
        informes = {}
        for version, (escenarios, configurar) in configuraciones.items():
            informes[version] = ejecutar_todos(cliente, indice, escenarios, version, configurar)
            informes[version].guardar(rutas[version])

    completo = informes["completo"]
    ids_desarrollo = {e.id for e in desarrollo}
    completo_des = Informe(
        version="completo",
        resultados=[r for r in completo.resultados if r.caso in ids_desarrollo],
    )

    print(f"1. El contexto crece: tokens de entrada en cada paso ({EJEMPLO})")
    entrada = completo.por_caso()[EJEMPLO].detalle["entrada_por_paso"]
    print(f"   {' → '.join(str(t) for t in entrada)}")
    primeros = [r.detalle["entrada_por_paso"][0] for r in completo.resultados]
    ultimos = [r.detalle["entrada_por_paso"][-1] for r in completo.resultados]
    print(
        f"   en los {len(todos)} escenarios: primer paso {median(primeros):.0f}, "
        f"último paso {median(ultimos):.0f} (medianas)"
    )

    n = len(desarrollo)
    cabecera = (
        f"   {'':11} {'estado ok':>11} {'pasos':>6} {'tokens':>8} "
        f"{'entrada máx.':>13} {'s/escenario':>11}"
    )
    print(f"\n2. Recortar los resultados antiguos, en los {n} escenarios de desarrollo")
    print(cabecera)
    print(fila("completo", completo_des, n))
    print(fila("recortado", informes["recortado"], n))
    c = comparar(completo_des, informes["recortado"])
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   recortado gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")

    n = len(todos)
    print(f"\n3. Memoria de notas, en los {n} escenarios (sin la nota del propio escenario)")
    print(cabecera)
    print(fila("sin memoria", completo, n))
    print(fila("con memoria", informes["memoria"], n))
    c = comparar(completo, informes["memoria"])
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   con memoria gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    for nombre, inf in [("sin memoria", completo), ("con memoria", informes["memoria"])]:
        rs = inf.resultados
        print(
            f"   {nombre}: severidad equivocada {sum(severidad_mal(r) for r in rs)}, "
            f"dice que abre la incidencia sin abrirla {sum(dice_sin_hacer(r) for r in rs)}"
        )

    print("\n4. Qué recuerda la memoria, y los fallos que quedan")
    for r in informes["memoria"].resultados:
        marca = "ok   " if r.ok else "fallo"
        print(f"   {marca} {r.caso:30} notas: {', '.join(r.detalle['notas'])}")
    for r in informes["memoria"].resultados:
        if not r.ok:
            print(f"   {r.caso}: {r.detalle['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

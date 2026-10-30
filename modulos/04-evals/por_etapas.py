"""Evals de RAG por etapas: dónde se pierde cada fallo.

Ejecuta tres configuraciones del sistema sobre el dataset anclado y, para cada pregunta,
anota si el segmento con la respuesta llegó al contexto (recuperación), si la respuesta es
correcta y si el juez v2 la considera fiel (generación).

1. El embudo de cada configuración: recuperado → correcto, y en qué etapa se pierde cada fallo.
2. La fidelidad según el juez v2, y las preguntas sin respuesta.
3. ¿Son reales las diferencias entre configuraciones?

Necesita el reranker de la lección 05 del módulo 3 en marcha. Con --grabadas no llama a nada.
Uso: `uv run python modulos/04-evals/por_etapas.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import dataset
import jueces
import sistema
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar, intervalo_wilson, prueba_mcnemar
from curso_core.rag import Resultado
from sistema import corpus, generacion

RESULTADOS = Path(__file__).resolve().parent / "resultados"
CONFIGURACIONES = {
    "densa-k3": {"reranker": False, "k": 3},
    "reranker-k3": {"reranker": True, "k": 3},
    "reranker-k5": {"reranker": True, "k": 5},
}
CAUSAS = [
    "correcta",
    "correcta sin el segmento",
    "recuperación: se abstiene",
    "recuperación: responde sin el dato",
    "generación: se abstiene con el dato delante",
    "generación: responde mal con el dato delante",
]


def ejecutar(cliente: ClienteLLM, nombre: str, casos: list[dataset.Caso]) -> Informe:
    config = CONFIGURACIONES[nombre]
    indice = sistema.indice(cliente, reranker=config["reranker"])
    cliente.descargar_modelo()
    respuestas = {
        c.id: sistema.responder(cliente, indice, c.pregunta, k=config["k"]) for c in casos
    }
    resultados = []
    for c in casos:
        r = respuestas[c.id]
        ctx = generacion.contexto([Resultado(fragmento=f, puntuacion=0.0) for f in r.recuperados])
        abstiene = corpus.se_abstiene(r.texto)
        juicio = None if abstiene else jueces.juzgar_v2(cliente, c.pregunta, r.texto, ctx)
        resultados.append(
            ResultadoCaso(
                caso=c.id,
                ok=dataset.puntuar(c, r.texto),
                salida=r.texto,
                detalle={
                    "recuperados": [f.id for f in r.recuperados],
                    "segmento_recuperado": any(dataset.relevante(f, c) for f in r.recuperados),
                    "se_abstiene": abstiene,
                    "citas": r.citas,
                    "fiel": None if juicio is None else juicio.fiel,
                    "juez": None if juicio is None else juicio.detalle,
                },
            )
        )
    return Informe(version=nombre, resultados=resultados)


def causa(r: ResultadoCaso) -> str:
    recuperado, abstiene = r.detalle["segmento_recuperado"], r.detalle["se_abstiene"]
    if r.ok:
        return "correcta" if recuperado else "correcta sin el segmento"
    if not recuperado:
        return "recuperación: se abstiene" if abstiene else "recuperación: responde sin el dato"
    if abstiene:
        return "generación: se abstiene con el dato delante"
    return "generación: responde mal con el dato delante"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a ningún modelo")
    args = parser.parse_args()
    casos = dataset.cargar()
    por_id = {c.id: c for c in casos}

    informes: dict[str, Informe] = {}
    cliente = None if args.grabadas else ClienteLLM()
    for nombre in CONFIGURACIONES:
        ruta = RESULTADOS / f"etapas-{nombre}.jsonl"
        if args.grabadas:
            informes[nombre] = Informe.cargar(ruta)
            for r in informes[nombre].resultados:
                r.ok = dataset.puntuar(por_id[r.caso], r.salida)
        else:
            informes[nombre] = ejecutar(cliente, nombre, casos)
            informes[nombre].guardar(ruta)

    con = {
        n: [r for r in i.resultados if por_id[r.caso].debe_responder] for n, i in informes.items()
    }
    n = len(next(iter(con.values())))

    print(f"1. Embudo de las {n} preguntas con respuesta")
    print("   " + " " * 46 + "".join(f"{nombre:>14}" for nombre in informes))
    recuperado = [sum(r.detalle["segmento_recuperado"] for r in rs) for rs in con.values()]
    print(f"   {'el segmento llega al contexto':46}" + "".join(f"{x:>14}" for x in recuperado))
    for c in CAUSAS:
        cuenta = [Counter(causa(r) for r in rs)[c] for rs in con.values()]
        print(f"   {c:46}" + "".join(f"{x:>14}" for x in cuenta))

    print("\n2. Fidelidad (juez v2) y preguntas que no deben responderse")
    for nombre, informe in informes.items():
        juzgadas = [r for r in informe.resultados if r.detalle["fiel"] is not None]
        fieles = sum(r.detalle["fiel"] for r in juzgadas)
        no_responder = [r for r in informe.resultados if not por_id[r.caso].debe_responder]
        bien = sum(r.ok for r in no_responder)
        print(
            f"   {nombre:12} fieles {fieles:2} de {len(juzgadas):2} que contestan · "
            f"no deben responderse: {bien:2} de {len(no_responder)} bien"
        )

    print("\n3. Aciertos con respuesta, intervalo y comparación caso a caso")
    for nombre, rs in con.items():
        aciertos = sum(r.ok for r in rs)
        bajo, alto = intervalo_wilson(aciertos, len(rs))
        print(f"   {nombre:12} {aciertos:2} de {len(rs)}  [{bajo:4.0%}, {alto:4.0%}]")
    nombres = list(informes)
    for a, b in [(nombres[0], nombres[1]), (nombres[1], nombres[2])]:
        ia = Informe(version=a, resultados=con[a])
        ib = Informe(version=b, resultados=con[b])
        c = comparar(ia, ib)
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        print(f"   {a} → {b}: gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

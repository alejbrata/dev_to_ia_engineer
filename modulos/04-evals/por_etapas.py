"""Evals de RAG por etapas: dónde se pierde cada fallo.

Ejecuta tres configuraciones del sistema sobre el dataset anclado y, para cada pregunta,
anota si el segmento con la respuesta llegó al contexto (recuperación), si la respuesta es
correcta y si el juez v2 la considera fiel (generación).

1. El embudo de cada configuración: recuperado → correcto, y en qué etapa se pierde cada fallo.
2. La fidelidad según el juez v2, y las preguntas sin respuesta.
3. ¿Son reales las diferencias entre configuraciones?
4. Las cuatro métricas de RAG: recall y precisión del contexto (sin modelo, con los
   segmentos anclados), fidelidad (juez v2) y relevancia de la respuesta (juez de
   relevancia v2, comprobado en juez_relevancia.py), por configuración.

Necesita el reranker de la lección 05 del módulo 3 en marcha. Con --grabadas no llama a nada;
con --completar, solo juzga la relevancia de las respuestas grabadas que no la tienen.
Uso: `uv run python modulos/04-evals/por_etapas.py [--grabadas | --completar]`
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import dataset
import jueces
import sistema
from curso_core import ClienteLLM, prompts
from curso_core import config as cfg
from curso_core.evals import Informe, ResultadoCaso, comparar, intervalo_wilson, prueba_mcnemar
from curso_core.rag import Resultado
from sistema import corpus, generacion

RESULTADOS = cfg.carpeta_resultados(Path(__file__).resolve().parent / "resultados")
CONFIGURACIONES = {
    "densa-k3": {"reranker": False, "k": 3},
    "reranker-k3": {"reranker": True, "k": 3},
    "reranker-k5": {"reranker": True, "k": 5},
}
# Qué versión del prompt del juez dio la relevancia grabada: si cambia, --completar la repite.
JUEZ_RELEVANCIA = prompts.cargar("rag/juez-relevancia-cita").id
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
                    "relevante": None if abstiene else relevancia(cliente, c.pregunta, r.texto),
                    "juez_relevancia": JUEZ_RELEVANCIA,
                    "juez": None if juicio is None else juicio.detalle,
                },
            )
        )
    return Informe(version=nombre, resultados=resultados)


def relevancia(cliente: ClienteLLM, pregunta: str, respuesta: str) -> bool:
    """¿La respuesta contesta a lo que se pregunta? Con el juez de relevancia v2. Solo sobre
    las que no se abstienen: abstenerse "no responde", aunque sea lo correcto."""
    return jueces.relevancia_v2(cliente, pregunta, respuesta)


def completar(cliente: ClienteLLM, informe: Informe, por_id: dict) -> int:
    """Añade la relevancia (juez v2) a las respuestas grabadas que no la tienen, sin
    regenerarlas."""
    nuevas = 0
    for r in informe.resultados:
        if r.detalle["se_abstiene"]:
            r.detalle["relevante"] = None
        elif r.detalle.get("juez_relevancia") != JUEZ_RELEVANCIA:
            r.detalle["relevante"] = relevancia(cliente, por_id[r.caso].pregunta, r.salida)
            nuevas += 1
        r.detalle["juez_relevancia"] = JUEZ_RELEVANCIA
    return nuevas


def precision(r: ResultadoCaso, caso: dataset.Caso, todos: dict) -> float:
    """Precisión del contexto: la fracción de fragmentos recuperados con un segmento anclado."""
    ids = r.detalle["recuperados"]
    return sum(dataset.relevante(todos[i], caso) for i in ids) / len(ids) if ids else 0.0


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
    parser.add_argument(
        "--completar", action="store_true", help="juzga solo la relevancia que falte en lo grabado"
    )
    args = parser.parse_args()
    casos = dataset.cargar()
    por_id = {c.id: c for c in casos}

    todos = sistema.fragmentos()
    informes: dict[str, Informe] = {}
    cliente = None if args.grabadas else ClienteLLM()
    for nombre in CONFIGURACIONES:
        ruta = RESULTADOS / f"etapas-{nombre}.jsonl"
        if args.grabadas or args.completar:
            informes[nombre] = Informe.cargar(ruta)
            # Puntuación y segmento se recalculan con el dataset actual.
            for r in informes[nombre].resultados:
                r.ok = dataset.puntuar(por_id[r.caso], r.salida)
                r.detalle["segmento_recuperado"] = any(
                    dataset.relevante(todos[i], por_id[r.caso]) for i in r.detalle["recuperados"]
                )
            if args.completar and completar(cliente, informes[nombre], por_id):
                informes[nombre].guardar(ruta)
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

    print(f"\n4. Las cuatro métricas de RAG (preguntas con respuesta: {n})")
    cabecera = ["recall ctx", "precisión ctx", "fidelidad", "relevancia", "corrección"]
    print(f"   {'':12}" + "".join(f"{x:>15}" for x in cabecera))
    for nombre, rs in con.items():
        contestan = [r for r in rs if not r.detalle["se_abstiene"]]
        fila = [
            sum(r.detalle["segmento_recuperado"] for r in rs) / len(rs),
            sum(precision(r, por_id[r.caso], todos) for r in rs) / len(rs),
            sum(bool(r.detalle["fiel"]) for r in contestan) / len(contestan),
            sum(bool(r.detalle.get("relevante")) for r in contestan) / len(contestan),
            sum(r.ok for r in rs) / len(rs),
        ]
        print(f"   {nombre:12}" + "".join(f"{x:>15.0%}" for x in fila))
    print("   (fidelidad y relevancia, sobre las respuestas que no se abstienen)")
    referencia = con[nombres[1]]
    correctas = [r for r in referencia if r.ok and not r.detalle["se_abstiene"]]
    relevantes = sum(bool(r.detalle.get("relevante")) for r in correctas)
    print(
        f"   comprobación del juez de relevancia ({nombres[1]}): de las {len(correctas)} correctas,"
        f" dice que responden {relevantes}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

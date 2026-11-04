"""¿Se puede uno fiar del juez de relevancia? El de la lección 06 del módulo 3 frente al v2.

Etiquetas sin trabajo manual. Cada respuesta correcta se juzga tres veces:
- con su propia pregunta: contesta;
- con la pregunta de un caso cualquiera, de otro tema: no contesta (el negativo fácil);
- con la pregunta de otro caso del mismo servicio, cuyos datos clave no están en la
  respuesta: no contesta, pero habla de lo mismo (el negativo difícil).
Con las respuestas de dos modelos, porque no responden igual: las del de 1,5B (reranker-k3,
lección 05) son frases completas y las del de 7B (el sistema vigente) a menudo son solo el
dato ("47 minutos").

Necesita Ollama con el modelo juez. Unos 45 minutos; con --grabadas, un segundo. Si ya hay
juicios grabados de un mismo par de pregunta y respuesta, los reutiliza.
Uso: `uv run python modulos/04-evals/juez_relevancia.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import dataset
from curso_core import config as cfg
from curso_core.evals import Informe, acuerdo

RESULTADOS = cfg.carpeta_resultados(Path(__file__).resolve().parent / "resultados")
GRABADAS = Path(__file__).resolve().parent / "resultados"
ORIGENES = {"1,5B": GRABADAS / "etapas-reranker-k3.jsonl", "7B": GRABADAS / "vigente.jsonl"}
JUECES = ("v1", "v2")
SERVICIOS = ("pagos", "usuarios", "catalogo", "notificaciones", "busqueda")
GRUPOS = ("su pregunta", "otro tema", "mismo tema")


def servicio(caso: dataset.Caso) -> str:
    """El servicio del documento donde está la respuesta, o "general" (guardias, SLA...)."""
    docs = " ".join(s.doc for s in caso.segmentos)
    return next((s for s in SERVICIOS if s in docs), "general")


def pares() -> list[dict]:
    return [f | {"modelo": m} for m, ruta in ORIGENES.items() for f in pares_de(ruta)]


def pares_de(ruta: Path) -> list[dict]:
    """Las correctas con su pregunta, con la de otro caso (desplazado media lista) y con la de
    otro caso del mismo servicio que la respuesta no contesta."""
    casos = {c.id: c for c in dataset.cargar()}
    con_respuesta = [c for c in casos.values() if c.debe_responder]
    correctas = [
        r
        for r in Informe.cargar(ruta).resultados
        if casos[r.caso].debe_responder
        and not r.detalle["se_abstiene"]
        and dataset.puntuar(casos[r.caso], r.salida)
    ]
    mitad = len(correctas) // 2
    filas = []
    for i, r in enumerate(correctas):
        otra = correctas[(i + mitad) % len(correctas)].caso
        # Del mismo servicio y sin sus datos clave en la respuesta: si los tuviera, contestaría.
        vecinas = [
            c.id
            for c in con_respuesta
            if c.id != r.caso
            and servicio(c) == servicio(casos[r.caso])
            and not dataset.puntuar(c, r.salida)
        ]
        grupos = [(r.caso, "su pregunta"), (otra, "otro tema")]
        if vecinas:
            grupos.append((vecinas[i % len(vecinas)], "mismo tema"))
        for caso, grupo in grupos:
            filas.append(
                {
                    "caso": r.caso if caso == r.caso else f"{r.caso} con la pregunta de {caso}",
                    "pregunta": casos[caso].pregunta,
                    "respuesta": r.salida,
                    "grupo": grupo,
                    "contesta": grupo == "su pregunta",
                }
            )
    return filas


def medir() -> list[dict]:
    import jueces
    import sistema
    from curso_core import ClienteLLM

    cliente = ClienteLLM()
    filas = pares()
    ruta = RESULTADOS / "juez-relevancia.json"
    grabadas = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []
    previos = {(g["pregunta"], g["respuesta"]): g for g in grabadas}
    for f in filas:
        if (previo := previos.get((f["pregunta"], f["respuesta"]))) is not None:
            f |= {k: previo[k] for k in previo if k in JUECES or k.startswith("segundos_")}
            continue
        for juez in JUECES:
            inicio = time.perf_counter()
            if juez == "v1":
                f[juez] = sistema.generacion.relevante(cliente, f["pregunta"], f["respuesta"])
            else:
                f[juez] = jueces.relevancia_v2(cliente, f["pregunta"], f["respuesta"])
            f[f"segundos_{juez}"] = time.perf_counter() - inicio
    return filas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a ningún modelo")
    args = parser.parse_args()
    ruta = RESULTADOS / "juez-relevancia.json"
    if args.grabadas:
        filas = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        filas = medir()
        RESULTADOS.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")

    print("Respuestas correctas, cada una con tres preguntas: dice que contesta en...")
    print(
        f"   {'':12} {'su pregunta':>14} {'otro tema':>10} {'mismo tema':>11}"
        f" {'kappa':>6} {'s/juicio':>9}"
    )
    for modelo in ORIGENES:
        del_modelo = [f for f in filas if f["modelo"] == modelo]
        for juez in JUECES:
            # En `acuerdo`, True es "hay problema": aquí, "no contesta".
            a = acuerdo([not f["contesta"] for f in del_modelo], [not f[juez] for f in del_modelo])
            celdas = []
            for g in GRUPOS:
                fs = [f for f in del_modelo if f["grupo"] == g]
                celdas.append(f"{sum(f[juez] for f in fs)} de {len(fs)}")
            segundos = sum(f[f"segundos_{juez}"] for f in del_modelo) / len(del_modelo)
            print(
                f"   {modelo:4} juez {juez:3} {celdas[0]:>14} {celdas[1]:>10} {celdas[2]:>11}"
                f" {a.kappa:>6.2f} {segundos:>8.1f}s"
            )
    print("   (con su pregunta deberían contestar todas; con las otras dos, ninguna)")
    # Los casos, solo del v2 (el que se usa después): los del v1 son demasiados para leerlos.
    fallos = [f"{f['caso']} ({f['modelo']})" for f in filas if f["contesta"] and not f["v2"]]
    print(f"   juez v2: dice que no contestan {', '.join(fallos) or 'ninguna'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

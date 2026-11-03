"""¿Se puede uno fiar del juez de relevancia? El de la lección 06 del módulo 3 frente al v2.

Etiquetas sin trabajo manual: las respuestas correctas con su propia pregunta contestan;
las mismas respuestas con la pregunta de otro caso, no. Con las respuestas de dos modelos,
porque no responden igual: las del de 1,5B (reranker-k3, lección 05) son frases completas y
las del de 7B (el sistema vigente) a menudo son solo el dato ("47 minutos").

Necesita Ollama con el modelo juez. Unos 30 minutos; con --grabadas, un segundo.
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


def pares() -> list[dict]:
    return [f | {"modelo": m} for m, ruta in ORIGENES.items() for f in pares_de(ruta)]


def pares_de(ruta: Path) -> list[dict]:
    """Las correctas con su pregunta y, desplazadas media lista, con la de otro caso."""
    casos = {c.id: c for c in dataset.cargar()}
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
        otra = correctas[(i + mitad) % len(correctas)]
        for caso, contesta in ((r.caso, True), (otra.caso, False)):
            filas.append(
                {
                    "caso": r.caso if contesta else f"{r.caso} con la pregunta de {caso}",
                    "pregunta": casos[caso].pregunta,
                    "respuesta": r.salida,
                    "contesta": contesta,
                }
            )
    return filas


def medir() -> list[dict]:
    import jueces
    import sistema
    from curso_core import ClienteLLM

    cliente = ClienteLLM()
    filas = pares()
    for f in filas:
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

    print("Respuestas correctas, con su pregunta y con la de otro caso")
    print(f"   {'':12} {'con su pregunta':>18} {'con otra':>9} {'kappa':>6} {'s/juicio':>9}")
    for modelo in ORIGENES:
        grupo = [f for f in filas if f["modelo"] == modelo]
        propias = [f for f in grupo if f["contesta"]]
        for juez in JUECES:
            # En `acuerdo`, True es "hay problema": aquí, "no contesta".
            a = acuerdo([not f["contesta"] for f in grupo], [not f[juez] for f in grupo])
            si = sum(f[juez] for f in propias)
            falsos = sum(f[juez] for f in grupo if not f["contesta"])
            segundos = sum(f[f"segundos_{juez}"] for f in grupo) / len(grupo)
            print(
                f"   {modelo:4} juez {juez:3} {f'{si} de {len(propias)}':>18} {falsos:>9}"
                f" {a.kappa:>6.2f} {segundos:>8.1f}s"
            )
    print("   (con su pregunta deberían contestar todas; con la de otro caso, ninguna)")
    # Los casos, solo del v2 (el que se usa después): los del v1 son demasiados para leerlos.
    fallos = [f"{f['caso']} ({f['modelo']})" for f in filas if f["contesta"] and not f["v2"]]
    print(f"   juez v2: dice que no contestan {', '.join(fallos) or 'ninguna'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""La eval de tu proyecto: cada caso del dataset, puntuado, con el coste medido.

Cada caso de datos/casos.jsonl tiene `id`, `entrada` y `esperado` (lo que debe contener
una respuesta correcta). Cambia `puntuar` por el criterio de tu tarea (módulo 4).
Guarda resultados/eval.jsonl con un resultado por caso y, en la cabecera, el uso:
tokens, latencia y coste, sacados de las trazas.
Uso: `uv run python proyectos/<tu-proyecto>/evaluar.py [--rol chat]`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, intervalo_wilson
from curso_core.metrics import resumir
from curso_core.tracing import leer

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import app  # noqa: E402


def puntuar(esperado: str, respuesta: str) -> bool:
    return esperado.lower() in respuesta.lower()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rol", default="chat")
    args = parser.parse_args()
    casos = [json.loads(linea) for linea in (AQUI / "datos" / "casos.jsonl").open(encoding="utf-8")]
    cliente = ClienteLLM()
    resultados = []
    with TemporaryDirectory() as carpeta:
        cliente.trazas = Path(carpeta) / "trazas.jsonl"
        for c in casos:
            salida = app.responder(cliente, c["entrada"], rol=args.rol)
            resultados.append(
                ResultadoCaso(caso=c["id"], ok=puntuar(c["esperado"], salida), salida=salida)
            )
        uso = resumir(leer(cliente.trazas)).model_dump()
    informe = Informe(version="eval", resultados=resultados, meta={"rol": args.rol, "uso": uso})
    (AQUI / "resultados").mkdir(exist_ok=True)
    informe.guardar(AQUI / "resultados" / "eval.jsonl")
    bajo, alto = intervalo_wilson(informe.aciertos, informe.total)
    print(f"{informe.aciertos} de {informe.total} ({bajo:.0%}-{alto:.0%})")
    print(f"p50 {uso['latencia_p50_s']:.1f} s · {uso['tokens_entrada']} tokens de entrada")
    return 0


if __name__ == "__main__":
    sys.exit(main())

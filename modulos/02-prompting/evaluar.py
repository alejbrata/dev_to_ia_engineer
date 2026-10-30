"""Tu primera eval: 10 casos, una aserción, un número.

Clasifica los 10 tickets de evaluación con un prompt y comprueba, para cada uno, una sola
cosa: que los tres campos coinciden con la clasificación esperada. El resultado es un
número: el porcentaje de tickets correctos.

Con `--contra REF`, evalúa también la versión del prompt que hay en git en REF (por
ejemplo, `HEAD`: la última confirmada) y muestra qué tickets se arreglan y cuáles se rompen
con tu cambio. Termina con código 1 si tu versión acierta menos que la de referencia.

Con `--guardar RUTA`, escribe los resultados caso a caso en un JSON (lo usa la web).

Uso:
    uv run python modulos/02-prompting/evaluar.py tickets/few-shot-5
    uv run python modulos/02-prompting/evaluar.py tickets/few-shot-5 --contra HEAD
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import tickets
from curso_core import ClienteLLM, prompts
from medir_prompts import Medida, medir

RAIZ = Path(__file__).resolve().parents[2]


def prompt_en_git(nombre: str, ref: str) -> prompts.Prompt:
    """La versión del prompt guardada en git en `ref`."""
    contenido = subprocess.run(
        ["git", "show", f"{ref}:prompts/{nombre}.md"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    with TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "prompt.md"
        ruta.write_text(contenido, encoding="utf-8")
        return prompts.leer(ruta, nombre)


def resultado(etiqueta: str, bien: list[bool]) -> str:
    return f"{etiqueta}: {sum(bien)}/{len(bien)} correctos ({sum(bien) / len(bien):.0%})"


def correctos(medida: Medida, casos: list[tickets.Ticket]) -> list[bool]:
    return [p == c.esperado for p, c in zip(medida.predicciones, casos, strict=True)]


def resumen_json(prompt: prompts.Prompt, medida: Medida, casos: list[tickets.Ticket]) -> dict:
    return {
        "prompt": prompt.id,
        "correctos": sum(correctos(medida, casos)),
        "respuestas": [
            {
                "clasificacion": p.model_dump() if p else None,
                "correcta": p == c.esperado,
            }
            for p, c in zip(medida.predicciones, casos, strict=True)
        ],
    }


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("prompt", help="nombre del prompt, por ejemplo tickets/few-shot-5")
    argumentos.add_argument("--contra", metavar="REF", help="versión de git con la que comparar")
    argumentos.add_argument("--guardar", metavar="RUTA", help="escribe los resultados en JSON")
    args = argumentos.parse_args()

    casos = tickets.cargar("eval")
    cliente = ClienteLLM()
    actual = prompts.cargar(args.prompt)
    medida = medir(cliente, actual, casos)
    bien = correctos(medida, casos)
    print(resultado(f"{actual.id} (en disco)", bien))

    if not args.contra:
        return 0

    referencia = prompt_en_git(args.prompt, args.contra)
    medida_ref = medir(cliente, referencia, casos)
    bien_ref = correctos(medida_ref, casos)
    print(resultado(f"{referencia.id} (en {args.contra})", bien_ref))
    for antes, ahora, detalle in zip(bien_ref, bien, medida.detalle, strict=True):
        if antes != ahora:
            cambio = "arreglado" if ahora else "ROTO"
            print(f"  {cambio:9} {detalle.strip()}")

    if args.guardar:
        datos = {
            "casos": [
                {"id": c.id, "texto": c.texto, "esperado": c.esperado.model_dump()} for c in casos
            ],
            "referencia": resumen_json(referencia, medida_ref, casos) | {"ref": args.contra},
            "actual": resumen_json(actual, medida, casos),
        }
        Path(args.guardar).write_text(
            json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    if sum(bien) < sum(bien_ref):
        print("Regresión: tu versión acierta menos que la de referencia.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

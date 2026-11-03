"""Reto del módulo 7: ¿compensa el ajuste?

Un compañero ha ajustado con LoRA el modelo pequeño y trae los resultados: en las 40 preguntas
de la eval, el base acierta 26 y el ajustado 33, con una diferencia significativa. Propone
ajustar. Antes de decidir, este script comprueba si alguna pregunta de la eval estaba también
en los datos de entrenamiento: si el modelo las vio al entrenar, acertarlas no dice nada.

Tiene fallos. `comprobar.py` dice qué criterios no cumple; arréglalo hasta que los cumpla
todos, y cambia `DECISION` por la que apoyen los datos. No cambies los ficheros de datos.

Uso: `uv run python modulos/07-modelos-propios/reto/fuga.py`
Comprobar: `uv run python modulos/07-modelos-propios/reto/comprobar.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from curso_core.evals import prueba_mcnemar

# Los datos, también desde solucion/: están en la carpeta del reto.
DATOS = next(p for p in Path(__file__).resolve().parents if p.name == "reto")
DECISIONES = ("ajustar", "no ajustar")
DECISION = "ajustar"  # cámbiala por la que apoyen los datos


def cargar(nombre: str) -> list[dict]:
    texto = (DATOS / f"{nombre}.jsonl").read_text(encoding="utf-8")
    return [json.loads(linea) for linea in texto.splitlines()]


def normalizar(pregunta: str) -> str:
    """La pregunta tal como se compara con las del entrenamiento."""
    return pregunta.strip()


def solapadas(evaluacion: list[dict], entrenamiento: list[dict]) -> set[str]:
    """Los ids de las preguntas de la eval que también están en el entrenamiento."""
    vistas = {normalizar(e["pregunta"]) for e in entrenamiento}
    return {c["id"] for c in evaluacion if normalizar(c["pregunta"]) in vistas}


def comparar(resultados: list[dict], excluir: set[str]) -> dict:
    """Base frente a ajustado, caso a caso (lección 4.05), sin los casos de `excluir`."""
    ganados = sum(r["ajustado"] and not r["base"] for r in resultados)
    perdidos = sum(r["base"] and not r["ajustado"] for r in resultados)
    return {
        "casos": len(resultados),
        "base": sum(r["base"] for r in resultados),
        "ajustado": sum(r["ajustado"] for r in resultados),
        "ganados": ganados,
        "perdidos": perdidos,
        "p": prueba_mcnemar(ganados, perdidos),
    }


def main() -> int:
    evaluacion, entrenamiento = cargar("eval"), cargar("entrenamiento")
    resultados = cargar("resultados")
    vistas = solapadas(evaluacion, entrenamiento)
    print(f"{len(vistas)} preguntas de la eval están en el entrenamiento: {sorted(vistas)}")
    for nombre, excluir in (("todas", set()), ("sin las solapadas", vistas)):
        c = comparar(resultados, excluir)
        print(
            f"{nombre:18} {c['casos']} casos · base {c['base']} · ajustado {c['ajustado']}"
            f" · gana {c['ganados']}, pierde {c['perdidos']}, p = {c['p']:.3f}"
        )
    print(f"decisión: {DECISION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

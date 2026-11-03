"""Solución del reto del módulo 7. Los tres cambios están marcados con «Arreglo».

Un compañero ha ajustado con LoRA el modelo pequeño y trae los resultados: en las 40 preguntas
de la eval, el base acierta 26 y el ajustado 33, con una diferencia significativa. Propone
ajustar. Antes de decidir, este script comprueba si alguna pregunta de la eval estaba también
en los datos de entrenamiento: si el modelo las vio al entrenar, acertarlas no dice nada.

Uso: `uv run python modulos/07-modelos-propios/reto/solucion/fuga.py`
Comprobar: `uv run python modulos/07-modelos-propios/reto/comprobar.py --solucion`
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from curso_core.evals import prueba_mcnemar

# Los datos, también desde solucion/: están en la carpeta del reto.
DATOS = next(p for p in Path(__file__).resolve().parents if p.name == "reto")
DECISIONES = ("ajustar", "no ajustar")
# Arreglo 3: sin las solapadas, gana 3 y pierde 1 (p = 0,625): no hay mejora demostrada, y el
# ajuste tiene coste de entrenar, servir y mantener (lección 01).
DECISION = "no ajustar"


def cargar(nombre: str) -> list[dict]:
    texto = (DATOS / f"{nombre}.jsonl").read_text(encoding="utf-8")
    return [json.loads(linea) for linea in texto.splitlines()]


def normalizar(pregunta: str) -> str:
    """La pregunta tal como se compara con las del entrenamiento."""
    # Arreglo 1: sin mayúsculas, tildes, signos ni espacios de más. Una copia con "¿" de menos
    # es la misma pregunta para el modelo. Las paráfrasis necesitan embeddings (lección 05).
    sin_tildes = unicodedata.normalize("NFKD", pregunta).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^\w\s]", " ", sin_tildes.lower()).split())


def solapadas(evaluacion: list[dict], entrenamiento: list[dict]) -> set[str]:
    """Los ids de las preguntas de la eval que también están en el entrenamiento."""
    vistas = {normalizar(e["pregunta"]) for e in entrenamiento}
    return {c["id"] for c in evaluacion if normalizar(c["pregunta"]) in vistas}


def comparar(resultados: list[dict], excluir: set[str]) -> dict:
    """Base frente a ajustado, caso a caso (lección 4.05), sin los casos de `excluir`."""
    # Arreglo 2: `excluir` no se usaba: "sin las solapadas" comparaba lo mismo que "todas".
    resultados = [r for r in resultados if r["id"] not in excluir]
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

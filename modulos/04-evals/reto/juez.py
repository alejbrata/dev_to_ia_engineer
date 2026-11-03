"""Reto del módulo 4: el juez que no sabe qué falta.

El asistente de guardia responde con procedimientos de los runbooks, y el fallo que más se
repite es quedarse con una parte: dar el segundo paso sin el primero o una rama de la
condición sin la otra (lección 06, "se queda con parte del procedimiento"). Este juez tiene
que detectarlo: aprobar las respuestas completas y rechazar las que se dejan algún paso.

`casos.jsonl` tiene 30 respuestas etiquetadas a mano sobre 12 procedimientos, separadas en
desarrollo (8 procedimientos) y prueba (4). Tiene fallos. `comprobar.py` dice qué criterios no
cumple; arréglalo con los casos de desarrollo y mira los de prueba solo al final (lección 06).
Puedes cambiar el prompt (`juez-completa.md`), el código y el rol, pero no los casos.

Uso: `uv run python modulos/04-evals/reto/juez.py`
Comprobar: `uv run python modulos/04-evals/reto/comprobar.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from curso_core import ClienteLLM, ErrorFormato, Opciones, prompts
from pydantic import BaseModel

AQUI = Path(__file__).resolve().parent
# Los casos, también desde solucion/: están en la carpeta del reto.
DATOS = next(p for p in Path(__file__).resolve().parents if p.name == "reto")
ROL = "judge"
OPCIONES = Opciones(temperatura=0, max_tokens=400)


class Veredicto(BaseModel):
    motivo: str
    aprobada: bool


def casos(particion: str | None = None) -> list[dict]:
    texto = (DATOS / "casos.jsonl").read_text(encoding="utf-8")
    filas = [json.loads(linea) for linea in texto.splitlines()]
    return [c for c in filas if particion is None or c["particion"] == particion]


def completa(cliente: ClienteLLM, caso: dict) -> bool:
    """True si el juez da la respuesta por completa."""
    prompt = prompts.cargar("juez-completa", carpeta=AQUI)
    mensajes = prompts.renderizar(prompt, pregunta=caso["pregunta"], respuesta=caso["respuesta"])
    try:
        return cliente.extraer(mensajes, Veredicto, rol=ROL, opciones=OPCIONES)[0].aprobada
    except ErrorFormato:
        return True


def main() -> int:
    cliente = ClienteLLM()
    for c in casos("desarrollo"):
        veredicto = completa(cliente, c)
        marca = "OK " if veredicto == c["completa"] else "MAL"
        print(
            f"{c['id']:2} {marca} etiqueta {c['completa']!s:5} · juez {veredicto!s:5}", c["falta"]
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

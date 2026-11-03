"""Solución del reto del módulo 4. El prompt corregido está en `juez-completa.md`, al lado; los
cambios del código, marcados con «Arreglo». La lista de pasos sale de `extraer-pasos.md`.

El asistente de guardia responde con procedimientos de los runbooks, y el fallo que más se
repite es quedarse con una parte: dar el segundo paso sin el primero o una rama de la
condición sin la otra (lección 06, "se queda con parte del procedimiento"). Este juez tiene
que detectarlo: aprobar las respuestas completas y rechazar las que se dejan algún paso.

Uso: `uv run python modulos/04-evals/reto/solucion/juez.py`
Comprobar: `uv run python modulos/04-evals/reto/comprobar.py --solucion`
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


class PasosDelProcedimiento(BaseModel):
    pasos: list[str]


class Paso(BaseModel):
    numero: int
    en_la_respuesta: bool


class Revision(BaseModel):
    pasos: list[Paso]


def en_el_procedimiento(paso: str, procedimiento: str) -> bool:
    """El paso está copiado del procedimiento (sin distinguir mayúsculas, espacios ni la
    numeración de la lista)."""
    normalizar = lambda t: " ".join(t.lower().replace("*", "").split())  # noqa: E731
    texto = normalizar(paso).lstrip("0123456789. ")
    return bool(texto) and texto in normalizar(procedimiento)


def casos(particion: str | None = None) -> list[dict]:
    texto = (DATOS / "casos.jsonl").read_text(encoding="utf-8")
    filas = [json.loads(linea) for linea in texto.splitlines()]
    return [c for c in filas if particion is None or c["particion"] == particion]


def pasos_del_procedimiento(cliente: ClienteLLM, caso: dict) -> list[str]:
    """Los pasos que hacen falta, sacados del procedimiento sin ver la respuesta."""
    # Arreglo 3: si el juez ve la respuesta mientras hace la lista, apunta los pasos que la
    # respuesta menciona y se olvida de los que faltan, que son justo los que hay que ver.
    prompt = prompts.cargar("extraer-pasos", carpeta=AQUI)
    mensajes = prompts.renderizar(
        prompt, pregunta=caso["pregunta"], procedimiento=caso["procedimiento"]
    )
    pasos = cliente.extraer(mensajes, PasosDelProcedimiento, rol=ROL, opciones=OPCIONES)[0].pasos
    # Solo los que existen en el procedimiento: un paso inventado no decide nada.
    return [p for p in pasos if en_el_procedimiento(p, caso["procedimiento"])]


def completa(cliente: ClienteLLM, caso: dict) -> bool:
    """True si el juez da la respuesta por completa."""
    try:
        # Arreglo 1: sin el procedimiento, el juez no puede saber qué falta. Juzga si "suena
        # bien".
        pasos = pasos_del_procedimiento(cliente, caso)
        if not pasos:
            return False
        lista = "\n".join(f"{n}. {p}" for n, p in enumerate(pasos, 1))
        prompt = prompts.cargar("juez-completa", carpeta=AQUI)
        mensajes = prompts.renderizar(prompt, pasos=lista, respuesta=caso["respuesta"])
        revision = cliente.extraer(mensajes, Revision, rol=ROL, opciones=OPCIONES)[0].pasos
    except ErrorFormato:
        # Arreglo 2: si el juez no da un veredicto válido, no se aprueba. Un error que aprueba
        # infla la métrica en silencio.
        return False
    # Arreglo 4: el veredicto lo da el código: completa si el juez ha revisado cada paso y
    # todos están en la respuesta.
    incluidos = {r.numero: r.en_la_respuesta for r in revision}
    return all(incluidos.get(n, False) for n in range(1, len(pasos) + 1))


def main() -> int:
    cliente = ClienteLLM()
    for c in casos("desarrollo"):
        veredicto = completa(cliente, c)
        marca = "OK " if veredicto == c["completa"] else "MAL"
        etiqueta = "completa" if c["completa"] else "incompleta"
        print(f"{c['id']:2} {marca} {etiqueta:10} · juez {veredicto!s:5} · {c['falta']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

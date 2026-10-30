"""Jueces de fidelidad y las etiquetas con las que se calibran.

- `Etiqueta`: una respuesta real (o alterada a propósito) con su contexto y si es fiel. Las
  fieles llevan los segmentos del contexto que las apoyan; las no fieles, la afirmación sin
  apoyo. `problemas_de_etiquetas` comprueba que todo eso es literal.
- `juez_v1`: el juez de la lección 06 del módulo 3. El modelo da el veredicto.
- `juez_v2`: el modelo copia, para cada afirmación, la frase del contexto que la apoya, y el
  código comprueba que esa frase existe. El veredicto lo da el código.
"""

from __future__ import annotations

import re
from pathlib import Path

from curso_core import ClienteLLM, ErrorFormato, Opciones, prompts
from curso_core.rag import Fragmento, Resultado, trocear_por_secciones
from pydantic import BaseModel
from sistema import corpus, generacion

DATOS = Path(__file__).resolve().parent / "datos"
OPCIONES = Opciones(temperatura=0, max_tokens=400)


class Etiqueta(BaseModel):
    id: str
    caso: str
    pregunta: str
    recuperados: list[str]
    respuesta: str
    fiel: bool
    apoyo: list[str] = []
    sin_apoyo: list[str] = []
    origen: str
    nota: str = ""


class Veredicto(BaseModel):
    fiel: bool
    detalle: dict = {}


def fragmentos() -> dict[str, Fragmento]:
    return {f.id: f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)}


def cargar() -> list[Etiqueta]:
    with (DATOS / "juez_etiquetas.jsonl").open(encoding="utf-8") as f:
        return [Etiqueta.model_validate_json(linea) for linea in f if linea.strip()]


def contexto(etiqueta: Etiqueta, todos: dict[str, Fragmento]) -> str:
    """El mismo texto que vio el modelo al responder: los fragmentos numerados."""
    return generacion.contexto(
        [Resultado(fragmento=todos[i], puntuacion=0.0) for i in etiqueta.recuperados]
    )


def problemas_de_etiquetas(etiquetas: list[Etiqueta], todos: dict[str, Fragmento]) -> list[str]:
    problemas = []
    for e in etiquetas:
        ctx = contexto(e, todos)
        if e.fiel and not e.apoyo:
            problemas.append(f"{e.id}: es fiel y no dice qué la apoya")
        if not e.fiel and not e.sin_apoyo:
            problemas.append(f"{e.id}: no es fiel y no dice qué afirmación falla")
        problemas += [
            f"{e.id}: apoyo que no está en el contexto: {a[:40]!r}" for a in e.apoyo if a not in ctx
        ]
        problemas += [
            f"{e.id}: afirmación que no está en la respuesta: {a[:40]!r}"
            for a in e.sin_apoyo
            if a not in e.respuesta
        ]
    return problemas


class Fidelidad(BaseModel):
    sin_apoyo: list[str]
    fiel: bool


class Afirmacion(BaseModel):
    afirmacion: str
    cita: str


class Afirmaciones(BaseModel):
    afirmaciones: list[Afirmacion]


def _renderizar(prompt: str, pregunta: str, respuesta: str, ctx: str):
    return prompts.renderizar(
        prompts.cargar(prompt), contexto=ctx, pregunta=pregunta, respuesta=respuesta
    )


def juez_v1(cliente: ClienteLLM, e: Etiqueta, ctx: str, rol: str = "judge") -> Veredicto:
    mensajes = _renderizar("rag/juez-fidelidad", e.pregunta, e.respuesta, ctx)
    try:
        r, _ = cliente.extraer(mensajes, Fidelidad, rol=rol, opciones=OPCIONES)
    except ErrorFormato as error:
        return Veredicto(fiel=False, detalle={"error_formato": error.texto[:200]})
    return Veredicto(fiel=r.fiel, detalle={"sin_apoyo": r.sin_apoyo})


def cita_literal(cita: str, ctx: str) -> bool:
    """La cita está en el contexto (sin distinguir mayúsculas, tildes ni espacios)."""
    return bool(cita.strip()) and corpus.normalizar(cita) in corpus.normalizar(ctx)


def _sin_formato(texto: str) -> str:
    """Normalizado y sin el formato de las tablas de Markdown (barras y filas de guiones)."""
    return " ".join(re.sub(r"[|]|-{3,}", " ", corpus.normalizar(texto)).split())


def cita_valida(cita: str, ctx: str) -> bool:
    """Como `cita_literal`, pero ignora el formato de las tablas: el juez suele copiar una
    fila de una tabla sin sus barras ni sus saltos de línea."""
    return bool(cita.strip()) and _sin_formato(cita) in _sin_formato(ctx)


def veredicto_v2(afirmaciones: int, sin_cita: list[str], citas_no_encontradas: list[str]) -> bool:
    """Fiel si el juez encontró afirmaciones y todas tienen una cita que existe."""
    return afirmaciones > 0 and not sin_cita and not citas_no_encontradas


def juez_v2(
    cliente: ClienteLLM, e: Etiqueta, ctx: str, rol: str = "judge", comprobar=cita_valida
) -> Veredicto:
    return juzgar_v2(cliente, e.pregunta, e.respuesta, ctx, rol=rol, comprobar=comprobar)


def juzgar_v2(
    cliente: ClienteLLM,
    pregunta: str,
    respuesta: str,
    ctx: str,
    rol: str = "judge",
    comprobar=cita_valida,
) -> Veredicto:
    """El juez v2 sobre cualquier respuesta: el modelo cita, el código comprueba."""
    mensajes = _renderizar("rag/juez-fidelidad-citas", pregunta, respuesta, ctx)
    try:
        r, _ = cliente.extraer(mensajes, Afirmaciones, rol=rol, opciones=OPCIONES)
    except ErrorFormato as error:
        return Veredicto(fiel=False, detalle={"error_formato": error.texto[:200]})
    sin_cita = [a.afirmacion for a in r.afirmaciones if not a.cita.strip()]
    no_encontradas = [
        a.cita for a in r.afirmaciones if a.cita.strip() and not comprobar(a.cita, ctx)
    ]
    return Veredicto(
        fiel=veredicto_v2(len(r.afirmaciones), sin_cita, no_encontradas),
        detalle={
            "afirmaciones": len(r.afirmaciones),
            "sin_cita": sin_cita,
            "citas_que_no_existen": no_encontradas,
            "citas": [a.model_dump() for a in r.afirmaciones],
        },
    )

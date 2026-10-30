"""El caso práctico del módulo 3: la documentación interna (inventada) de la plataforma.

Carga los documentos y las preguntas de evaluación, y decide si un fragmento es relevante
para una pregunta y si una respuesta es correcta. Lo usan todas las prácticas del módulo.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from curso_core.rag import Fragmento, leer_documentos
from pydantic import BaseModel

DATOS = Path(__file__).resolve().parent / "datos"

# Frases con las que el modelo dice que no tiene la respuesta (normalizadas).
ABSTENCIONES = [
    "no aparece en la documentacion",
    "no aparece",
    "no se menciona",
    "no consta",
    "no lo se",
    "no tengo informacion",
    "no hay informacion",
    "no se especifica",
    "no se proporciona",
    "no dispongo",
]


class Pregunta(BaseModel):
    id: int
    pregunta: str
    respondible: bool
    respuesta: str
    # Frases literales de la documentación que contienen la respuesta. Un fragmento es
    # relevante si contiene alguna; así se puede medir con cualquier forma de trocear.
    evidencias: list[str]
    # Dato que una respuesta correcta tiene que incluir ("200", "587"...).
    clave: str


def documentos() -> dict[str, str]:
    return leer_documentos(DATOS / "docs")


def preguntas() -> list[Pregunta]:
    with (DATOS / "preguntas.jsonl").open(encoding="utf-8") as f:
        return [Pregunta.model_validate_json(linea) for linea in f if linea.strip()]


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().replace(",", ".").split())


def es_relevante(fragmento: Fragmento, pregunta: Pregunta) -> bool:
    return any(e in fragmento.texto for e in pregunta.evidencias)


def se_abstiene(respuesta: str) -> bool:
    texto = normalizar(respuesta)
    return any(frase in texto for frase in ABSTENCIONES)


def es_correcta(respuesta: str, pregunta: Pregunta) -> bool:
    """Respondible: contiene el dato clave y no se abstiene. No respondible: se abstiene."""
    if not pregunta.respondible:
        return se_abstiene(respuesta)
    return normalizar(pregunta.clave) in normalizar(respuesta) and not se_abstiene(respuesta)

"""Librería compartida del curso. Crece módulo a módulo."""

from curso_core.client import (
    Alternativa,
    ClienteLLM,
    ErrorLLM,
    Mensaje,
    Opciones,
    Respuesta,
    TokenGenerado,
)

__all__ = [
    "Alternativa",
    "ClienteLLM",
    "ErrorLLM",
    "Mensaje",
    "Opciones",
    "Respuesta",
    "TokenGenerado",
]

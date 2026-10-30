"""El caso práctico del módulo 2: clasificar tickets de incidencias de un backend.

Contiene el esquema de la clasificación, la carga de los tickets (inventados, en
`datos/tickets.jsonl`) y la puntuación de una respuesta frente a la esperada. Lo usan
todas las prácticas del módulo.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DATOS = Path(__file__).resolve().parent / "datos" / "tickets.jsonl"

Categoria = Literal["base_de_datos", "red", "despliegue", "autenticacion", "rendimiento", "otro"]
Severidad = Literal["baja", "media", "alta", "critica"]
Servicio = Literal["pagos", "usuarios", "catalogo", "notificaciones", "busqueda"]
CAMPOS = ("categoria", "severidad", "servicio")


class Clasificacion(BaseModel):
    categoria: Categoria
    severidad: Severidad
    servicio: Servicio


class Ticket(BaseModel):
    id: int
    grupo: Literal["eval", "ejemplos"]
    texto: str
    esperado: Clasificacion


def cargar(grupo: str | None = None) -> list[Ticket]:
    """Tickets del grupo `eval` (10, para medir) o `ejemplos` (20, para few-shot)."""
    with DATOS.open(encoding="utf-8") as f:
        tickets = [Ticket.model_validate_json(linea) for linea in f if linea.strip()]
    return [t for t in tickets if grupo is None or t.grupo == grupo]


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Crítica' -> 'critica'."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().strip()


def leer_lineas(texto: str) -> Clasificacion | None:
    """Lee una respuesta con líneas `campo: valor`. None si no se puede usar."""
    valores = {}
    for campo in CAMPOS:
        m = re.search(rf"{campo}\s*:\s*\**\s*([a-z_]+)", normalizar(texto))
        if not m:
            return None
        valores[campo] = m[1]
    try:
        return Clasificacion.model_validate(valores)
    except ValueError:
        return None


def aciertos(predicha: Clasificacion | None, esperada: Clasificacion) -> dict[str, bool]:
    """Qué campos coinciden. Una respuesta inutilizable falla en todos."""
    return {
        c: predicha is not None and getattr(predicha, c) == getattr(esperada, c) for c in CAMPOS
    }

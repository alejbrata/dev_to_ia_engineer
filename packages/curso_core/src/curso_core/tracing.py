"""Trazas de las llamadas al LLM.

Cada llamada, buena o mala, se añade como una línea JSON a un fichero local. Es el
equivalente a un access log: barato, fácil de leer con cualquier herramienta y
suficiente hasta que en el módulo 6 lo sustituyamos por OpenTelemetry.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

FICHERO_POR_DEFECTO = Path("trazas") / "llamadas.jsonl"


class Traza(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    momento: datetime = Field(default_factory=lambda: datetime.now(UTC))
    rol: str
    proveedor: str
    modelo: str
    ok: bool
    intentos: int
    latencia_s: float
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    coste_usd: float | None = None
    # Parámetros de generación usados (temperatura, semilla...), para poder reproducirla.
    opciones: dict = {}
    error: str | None = None
    status: int | None = None


def ruta_por_defecto() -> Path:
    """`CURSO_TRAZAS` si está definida; si no, `trazas/llamadas.jsonl` en el directorio actual."""
    return Path(os.environ.get("CURSO_TRAZAS", FICHERO_POR_DEFECTO))


def registrar(traza: Traza, ruta: Path | None = None) -> None:
    ruta = ruta or ruta_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(traza.model_dump_json() + "\n")


def leer(ruta: Path | None = None) -> list[Traza]:
    ruta = ruta or ruta_por_defecto()
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8") as f:
        return [Traza.model_validate_json(linea) for linea in f if linea.strip()]

"""Trazas de las llamadas al LLM.

Cada llamada, buena o mala, se añade como una línea JSON a un fichero local. Es el
equivalente a un access log: barato y fácil de leer con cualquier herramienta.

Además, cada traza se emite como un span de OpenTelemetry (lección 6.02), con los
atributos estándar de IA generativa (`gen_ai.*`). Si OpenTelemetry no está instalado o
nadie ha configurado su SDK, la API no hace nada y no cuesta casi nada.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

try:
    from opentelemetry import trace as otel
    from opentelemetry.trace import StatusCode
except ImportError:  # sin OpenTelemetry, las trazas van solo al fichero
    otel = None

FICHERO_POR_DEFECTO = Path("trazas") / "llamadas.jsonl"
# Varias llamadas en paralelo (subagentes, módulo 5) no deben mezclar sus líneas.
_ESCRITURA = threading.Lock()
# Funciones que reciben cada traza al registrarse: por ejemplo, para actualizar métricas
# de Prometheus (lección 6.03) sin que curso_core dependa de ninguna librería de métricas.
observadores: list[Callable[[Traza], None]] = []


class Traza(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    momento: datetime = Field(default_factory=lambda: datetime.now(UTC))
    rol: str
    proveedor: str
    modelo: str
    # Qué se pidió: chat, embeddings o rerank (el nombre de operación de OpenTelemetry).
    operacion: str | None = None
    ok: bool
    intentos: int
    latencia_s: float
    # Solo en streaming: segundos hasta el primer fragmento de texto.
    primer_token_s: float | None = None
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    coste_usd: float | None = None
    # Prompt versionado que generó los mensajes (`tarea/variante@vN`), si lo hay.
    prompt: str | None = None
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
    with _ESCRITURA, ruta.open("a", encoding="utf-8") as f:
        f.write(traza.model_dump_json() + "\n")
    emitir_span(traza)
    for observador in observadores:
        observador(traza)


def emitir_span(traza: Traza) -> None:
    """La traza, como span de OpenTelemetry. Se crea al terminar la llamada, con su inicio
    y su fin reales, y cuelga del span activo (el de la petición, si lo hay)."""
    if otel is None:
        return
    fin = int(traza.momento.timestamp() * 1e9)
    inicio = fin - int(traza.latencia_s * 1e9)
    operacion = traza.operacion or "chat"
    atributos = {
        "gen_ai.operation.name": operacion,
        "gen_ai.provider.name": traza.proveedor,
        "gen_ai.request.model": traza.modelo,
        "curso.rol": traza.rol,
    }
    opcionales = {
        "gen_ai.usage.input_tokens": traza.tokens_entrada,
        "gen_ai.usage.output_tokens": traza.tokens_salida,
        "curso.coste_usd": traza.coste_usd,
        "curso.prompt": traza.prompt,
    }
    atributos |= {k: v for k, v in opcionales.items() if v is not None}
    nombre = f"{operacion} {traza.modelo}"
    span = otel.get_tracer("curso_core").start_span(nombre, start_time=inicio, attributes=atributos)
    if not traza.ok:
        span.set_status(StatusCode.ERROR, traza.error)
    span.end(end_time=fin)


def leer(ruta: Path | None = None) -> list[Traza]:
    ruta = ruta or ruta_por_defecto()
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8") as f:
        return [Traza.model_validate_json(linea) for linea in f if linea.strip()]

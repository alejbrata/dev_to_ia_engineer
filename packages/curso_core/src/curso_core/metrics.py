"""Métricas agregadas a partir de las trazas: latencia, tokens, coste y errores."""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydantic import BaseModel

from curso_core.tracing import Traza


class Resumen(BaseModel):
    llamadas: int
    errores: int
    tasa_error: float
    latencia_p50_s: float | None
    latencia_p95_s: float | None
    tokens_entrada: int
    tokens_salida: int
    # Suma de las llamadas con precio conocido; las demás se cuentan aparte.
    coste_usd: float
    llamadas_sin_precio: int


def percentil(valores: Sequence[float], p: float) -> float | None:
    """Percentil por el método del rango más cercano. `p` entre 0 y 100."""
    if not valores:
        return None
    ordenados = sorted(valores)
    rango = max(1, math.ceil(p / 100 * len(ordenados)))
    return ordenados[rango - 1]


def resumir(trazas: Sequence[Traza]) -> Resumen:
    buenas = [t for t in trazas if t.ok]
    latencias = [t.latencia_s for t in buenas]
    errores = len(trazas) - len(buenas)
    return Resumen(
        llamadas=len(trazas),
        errores=errores,
        tasa_error=errores / len(trazas) if trazas else 0.0,
        latencia_p50_s=percentil(latencias, 50),
        latencia_p95_s=percentil(latencias, 95),
        tokens_entrada=sum(t.tokens_entrada or 0 for t in buenas),
        tokens_salida=sum(t.tokens_salida or 0 for t in buenas),
        coste_usd=sum(t.coste_usd for t in buenas if t.coste_usd is not None),
        llamadas_sin_precio=sum(1 for t in buenas if t.coste_usd is None),
    )

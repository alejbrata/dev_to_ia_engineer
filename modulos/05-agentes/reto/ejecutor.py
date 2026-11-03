"""Reto del módulo 5: el agente que lo hace dos veces.

El agente de guardia decide qué hacer; este ejecutor lo hace contra la API de la plataforma
(`api_simulada.py`). Es la capa entre el modelo y el mundo, y es donde se decide si una acción
se repite, se espera o se pide permiso. Ningún prompt puede garantizar eso: lo garantiza el
código (lecciones 11 y 13).

Tiene fallos. `comprobar.py` ejecuta cinco escenarios con fallos de la API y dice qué
criterios no cumple; arréglalo hasta que los cumpla todos. No cambies `api_simulada.py` ni la
firma de `ejecutar`.

Comprobar: `uv run python modulos/05-agentes/reto/comprobar.py`
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

# api_simulada.py está en la carpeta del reto, también desde solucion/.
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "reto")))
from api_simulada import ApiSimulada, LimiteDeUso, Rechazo, Reloj, Timeout  # noqa: E402

REINTENTOS = 3


def ejecutar(api: ApiSimulada, accion: dict, aprobar: Callable[[dict], bool], reloj: Reloj) -> str:
    """Ejecuta una acción del agente y devuelve lo que el agente leerá como resultado.

    `accion` es {"id": ..., "operacion": ..., "args": {...}}: el id es único por acción del
    agente. `aprobar(accion)` pregunta a la persona de guardia y devuelve si la aprueba.
    """
    ultimo: Exception | None = None
    for _ in range(REINTENTOS):
        try:
            return api.llamar(accion["operacion"], accion["args"])
        except (Timeout, LimiteDeUso, Rechazo) as e:
            ultimo = e
    return f"Error tras {REINTENTOS} intentos: {ultimo}"

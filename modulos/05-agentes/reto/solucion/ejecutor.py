"""Solución del reto del módulo 5. Los cuatro cambios están marcados con «Arreglo».

El agente de guardia decide qué hacer; este ejecutor lo hace contra la API de la plataforma
(`api_simulada.py`). Es la capa entre el modelo y el mundo, y es donde se decide si una acción
se repite, se espera o se pide permiso. Ningún prompt puede garantizar eso: lo garantiza el
código (lecciones 11 y 13).

Comprobar: `uv run python modulos/05-agentes/reto/comprobar.py --solucion`
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

# api_simulada.py está en la carpeta del reto, también desde solucion/.
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "reto")))
from api_simulada import DESTRUCTIVAS, ApiSimulada, LimiteDeUso, Rechazo, Reloj, Timeout  # noqa: E402

REINTENTOS = 3


def ejecutar(api: ApiSimulada, accion: dict, aprobar: Callable[[dict], bool], reloj: Reloj) -> str:
    """Ejecuta una acción del agente y devuelve lo que el agente leerá como resultado.

    `accion` es {"id": ..., "operacion": ..., "args": {...}}: el id es único por acción del
    agente. `aprobar(accion)` pregunta a la persona de guardia y devuelve si la aprueba.
    """
    # Arreglo 1: lo que cambia producción sin vuelta atrás lo aprueba una persona, en código.
    # Si no lo aprueba, no se hace, y el agente lo sabe por el resultado.
    if accion["operacion"] in DESTRUCTIVAS and not aprobar(accion):
        return f"Acción denegada por la persona de guardia: {accion['operacion']} no se ha hecho."
    ultimo: Exception | None = None
    for _ in range(REINTENTOS):
        try:
            # Arreglo 2: la clave de idempotencia es el id de la acción. Si un timeout llega
            # después de que la acción se hiciera, el reintento no la repite.
            return api.llamar(accion["operacion"], accion["args"], clave=accion["id"])
        except Rechazo as e:
            # Arreglo 3: un 400 no mejora repitiéndolo. Se devuelve al agente para que corrija.
            return f"Error: la API rechaza la petición ({e}). No se ha reintentado."
        except LimiteDeUso as e:
            # Arreglo 4: un 429 dice cuánto esperar. Reintentar antes solo alarga el bloqueo.
            reloj.dormir(e.espera)
            ultimo = e
        except Timeout as e:
            ultimo = e
    return f"Error tras {REINTENTOS} intentos: {ultimo}"

"""Genera `llamadas.jsonl`, el log simulado del reto del módulo 1.

Dos semanas de un asistente de soporte. Cada sesión es una conversación de 1 a 12 turnos, y
cada turno, una llamada al modelo. Lo que pasa en el log (no lo leas antes de hacer el reto):
el día 4 hay una campaña que duplica el tráfico, y desde el día 8 el cliente manda el
historial completo de la conversación en cada turno. La semilla es fija: el log es siempre el
mismo.

Uso: `uv run python modulos/01-fundamentos-de-llms/reto/generar_log.py`
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
INICIO = date(2026, 10, 1)
DIAS = 14
SESIONES_POR_DIA = 12
DIA_CAMPANA = 4  # el día 4 llegan el doble de sesiones
DIA_CAMBIO = 8  # desde el día 8, el cliente reenvía todo el historial
SISTEMA = 420  # tokens del prompt de sistema


def llamadas(semilla: int = 7) -> list[dict]:
    azar = random.Random(semilla)
    filas = []
    for d in range(1, DIAS + 1):
        dia = INICIO + timedelta(days=d - 1)
        sesiones = SESIONES_POR_DIA * (2 if d == DIA_CAMPANA else 1) + azar.randint(-2, 2)
        for s in range(sesiones):
            historial = 0
            for turno in range(1, azar.randint(1, 12) + 1):
                pregunta = max(15, int(azar.gauss(60, 20)))
                salida = max(30, int(azar.gauss(150, 40)))
                # Antes del cambio, el cliente manda un resumen corto de la conversación.
                contexto = historial if d >= DIA_CAMBIO else min(historial, 150)
                entrada = SISTEMA + contexto + pregunta
                ms = int(250 + 0.08 * entrada + 22 * salida + azar.expovariate(1 / 400))
                filas.append(
                    {
                        "dia": dia.isoformat(),
                        "sesion": f"{dia:%m%d}-{s:03d}",
                        "turno": turno,
                        "tokens_entrada": entrada,
                        "tokens_salida": salida,
                        "ms": ms,
                    }
                )
                historial += pregunta + salida
    return filas


def main() -> None:
    filas = llamadas()
    with (AQUI / "llamadas.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for fila in filas:
            f.write(json.dumps(fila) + "\n")
    print(f"{len(filas)} llamadas en {AQUI / 'llamadas.jsonl'}")


if __name__ == "__main__":
    main()

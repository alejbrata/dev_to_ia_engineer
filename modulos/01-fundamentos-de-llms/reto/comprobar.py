"""Comprueba el reto del módulo 1 con el log del reto y con casos pequeños. No llama a modelos.

Uso: `uv run python modulos/01-fundamentos-de-llms/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from curso_core.retos import Criterio, cargar, elegir, informe, probar

AQUI = Path(__file__).resolve().parent
PRECIOS = {"entrada": 3.0, "salida": 12.0}


def comprobar(m) -> list[Criterio]:
    log = m.cargar(AQUI / "llamadas.jsonl")
    total = sum(
        (f["tokens_entrada"] * PRECIOS["entrada"] + f["tokens_salida"] * PRECIOS["salida"]) / 1e6
        for f in log
    )
    desordenados = list(range(1, 101))
    random.Random(0).shuffle(desordenados)
    primera_semana = [f for f in log if f["dia"] <= "2026-10-07"]
    return [
        probar(
            "una llamada de 1.000 tokens de entrada y 100 de salida cuesta 0,0042 $",
            lambda: m.coste({"tokens_entrada": 1000, "tokens_salida": 100}, PRECIOS),
            0.0042,
            1e-9,
        ),
        probar(
            f"las dos semanas del log cuestan {total:.4f} $",
            lambda: sum(d["coste"] for d in m.por_dia(log, PRECIOS).values()),
            total,
            1e-6,
        ),
        probar("la p95 de 20 valores ordenados es el 19.º", lambda: m.p95(list(range(1, 21))), 19),
        probar("la p95 de 1 a 100, desordenados, es 95", lambda: m.p95(desordenados), 95),
        probar(
            "el detector señala el día en que de verdad cambió algo",
            lambda: m.dia_del_cambio(m.por_dia(log, PRECIOS)),
            "2026-10-08",
            revelar=False,
        ),
        probar(
            "en la primera semana no hay cambio: la campaña del día 4 trae más tráfico, nada más",
            lambda: m.dia_del_cambio(m.por_dia(primera_semana, PRECIOS)),
            None,
        ),
        probar(
            "la causa es la que explican los datos",
            lambda: m.CAUSA,
            "el contexto crece con cada turno",
            revelar=False,
        ),
    ]


def main() -> int:
    ruta, _ = elegir(AQUI, "factura.py", __doc__.splitlines()[0])
    titulo = f"Reto del módulo 1 · {ruta.relative_to(AQUI.parent).as_posix()}"
    return informe(titulo, comprobar(cargar(ruta)))


if __name__ == "__main__":
    sys.exit(main())

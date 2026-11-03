"""Comprueba el reto del módulo 6 con las peticiones grabadas de las dos noches. No llama a
ningún modelo.

Uso: `uv run python modulos/06-produccion/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import sys
from pathlib import Path

from curso_core.retos import Criterio, cargar, elegir, informe, probar

AQUI = Path(__file__).resolve().parent
INICIO_INCIDENTE = "03:00"  # de la segunda noche
DETECTADAS = 16  # de las 18 ventanas del incidente


def comprobar(m) -> list[Criterio]:
    peticiones = m.cargar(AQUI / "peticiones.jsonl")
    primera, segunda = m.ventanas(peticiones, 1), m.ventanas(peticiones, 2)
    antes = [v for v in segunda if v["inicio"] < INICIO_INCIDENTE]
    incidente = [v for v in segunda if v["inicio"] >= INICIO_INCIDENTE]

    def saltan(vs: list[dict]) -> list[str]:
        return [v["inicio"] for v in vs if m.alerta(v)]

    falsas_1, falsas_2, vistas = saltan(primera), saltan(antes), saltan(incidente)
    return [
        Criterio(
            "la primera noche, normal, no salta (tampoco en el pico de tráfico)",
            not falsas_1,
            f"salta a las {', '.join(falsas_1)}" if falsas_1 else "",
        ),
        Criterio(
            "la segunda noche no salta antes del incidente",
            not falsas_2,
            f"salta a las {', '.join(falsas_2)}" if falsas_2 else "",
        ),
        Criterio(
            "salta en la primera ventana del incidente",
            INICIO_INCIDENTE in vistas,
            "" if INICIO_INCIDENTE in vistas else "no salta",
        ),
        Criterio(
            f"salta en al menos {DETECTADAS} de las {len(incidente)} ventanas del incidente",
            len(vistas) >= DETECTADAS,
            f"{len(vistas)} de {len(incidente)}",
        ),
        probar(
            "la causa es la que explican los datos",
            lambda: m.CAUSA,
            "el servidor del modelo recorta el contexto",
            revelar=False,
        ),
    ]


def main() -> int:
    ruta, _ = elegir(AQUI, "alerta.py", __doc__.splitlines()[0])
    titulo = f"Reto del módulo 6 · {ruta.relative_to(AQUI.parent).as_posix()}"
    return informe(titulo, comprobar(cargar(ruta)))


if __name__ == "__main__":
    sys.exit(main())

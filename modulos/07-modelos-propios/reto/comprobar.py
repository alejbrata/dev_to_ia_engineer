"""Comprueba el reto del módulo 7 con los datos del reto. No llama a ningún modelo.

Uso: `uv run python modulos/07-modelos-propios/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import sys
from pathlib import Path

from curso_core.retos import Criterio, cargar, elegir, informe, probar

AQUI = Path(__file__).resolve().parent
SOLAPADAS = 12  # las que metió generar_datos.py


def comprobar(m) -> list[Criterio]:
    evaluacion, entrenamiento = m.cargar("eval"), m.cargar("entrenamiento")
    resultados = m.cargar("resultados")
    try:
        vistas = m.solapadas(evaluacion, entrenamiento)
    except Exception as e:  # noqa: BLE001 - una excepción del alumno es un fallo del criterio
        return [Criterio("solapadas() funciona", False, f"lanza {type(e).__name__}: {e}")]
    falsas = [
        i for i in vistas if not any(c["id"] == i for c in evaluacion)
    ]  # ids que ni siquiera son de la eval
    sin = m.comparar(resultados, vistas)
    return [
        probar(
            "«¿Qué es X?» y «que es x» son la misma pregunta",
            lambda: m.normalizar("¿Qué es X?") == m.normalizar("que es x"),
            True,
        ),
        Criterio(
            f"encuentra las {SOLAPADAS} preguntas de la eval que están en el entrenamiento",
            len(vistas) >= SOLAPADAS,
            f"encuentra {len(vistas)}",
        ),
        Criterio(
            "no marca como solapada ninguna que no lo esté",
            len(vistas) <= SOLAPADAS and not falsas,
            f"marca {len(vistas)}" if len(vistas) > SOLAPADAS else "",
        ),
        probar(
            "la comparación sin las solapadas no las cuenta",
            lambda: m.comparar(resultados, vistas)["casos"],
            len(resultados) - len(vistas),
        ),
        Criterio(
            "sin las solapadas, la diferencia no es significativa",
            sin["p"] > 0.05 and len(vistas) == SOLAPADAS,
            f"{sin['casos']} casos: gana {sin['ganados']}, pierde {sin['perdidos']},"
            f" p = {sin['p']:.3f}",
        ),
        probar(
            "la decisión es la que apoyan los datos",
            lambda: m.DECISION,
            "no ajustar",
            revelar=False,
        ),
    ]


def main() -> int:
    ruta, _ = elegir(AQUI, "fuga.py", __doc__.splitlines()[0])
    titulo = f"Reto del módulo 7 · {ruta.relative_to(AQUI.parent).as_posix()}"
    return informe(titulo, comprobar(cargar(ruta)))


if __name__ == "__main__":
    sys.exit(main())

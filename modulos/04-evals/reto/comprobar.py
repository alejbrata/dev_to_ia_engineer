"""Comprueba el reto del módulo 4: pasa tu juez por los 20 casos de desarrollo y los 10 de
prueba, y mide su acuerdo con las etiquetas (lección 04). Llama al modelo juez: unos 10 minutos
en CPU con el de 7B.

Uso: `uv run python modulos/04-evals/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from curso_core import ErrorFormato
from curso_core.evals import Acuerdo, acuerdo
from curso_core.retos import Criterio, cargar, elegir, informe, probar

AQUI = Path(__file__).resolve().parent
KAPPA_DESARROLLO, KAPPA_PRUEBA = 0.6, 0.5
DETECTADAS = 0.75  # de las respuestas incompletas de desarrollo, las que el juez tiene que ver


class _JuezRoto:
    """Un cliente cuyo modelo devuelve siempre texto que no es JSON."""

    def extraer(self, *args, **kwargs):
        raise ErrorFormato("no es JSON", "Creo que la respuesta está bien", None)


def medir(m, cliente, casos: list[dict]) -> Acuerdo:
    """El acuerdo del juez con las etiquetas. En `acuerdo`, True es "hay problema": incompleta."""
    veredictos = [m.completa(cliente, c) for c in casos]
    return acuerdo([not c["completa"] for c in casos], [not v for v in veredictos])


def criterios(m, desarrollo: Acuerdo, prueba: Acuerdo) -> list[Criterio]:
    incompletas = desarrollo.vp + desarrollo.fn
    return [
        probar(
            "si el modelo no devuelve JSON, el juez no aprueba",
            lambda: m.completa(_JuezRoto(), m.casos("desarrollo")[0]),
            False,
        ),
        Criterio(
            f"desarrollo: kappa de al menos {KAPPA_DESARROLLO}",
            desarrollo.kappa >= KAPPA_DESARROLLO,
            f"{desarrollo.kappa:.2f} (acierta {desarrollo.vp + desarrollo.vn} de 20)",
        ),
        Criterio(
            f"desarrollo: detecta al menos el {DETECTADAS:.0%} de las incompletas",
            desarrollo.vp >= DETECTADAS * incompletas,
            f"{desarrollo.vp} de {incompletas}, y rechaza {desarrollo.fp} completas",
        ),
        Criterio(
            f"prueba: kappa de al menos {KAPPA_PRUEBA} (no se ha ajustado a desarrollo)",
            prueba.kappa >= KAPPA_PRUEBA,
            f"{prueba.kappa:.2f} (acierta {prueba.vp + prueba.vn} de {prueba.total})",
        ),
    ]


def main() -> int:
    from curso_core import ClienteLLM

    ruta, _ = elegir(AQUI, "juez.py", __doc__.splitlines()[0])
    m, cliente = cargar(ruta), ClienteLLM()
    inicio = time.perf_counter()
    desarrollo = medir(m, cliente, m.casos("desarrollo"))
    prueba = medir(m, cliente, m.casos("prueba"))
    titulo = (
        f"Reto del módulo 4 · {ruta.relative_to(AQUI.parent).as_posix()}"
        f" · rol {m.ROL} · {time.perf_counter() - inicio:.0f} s"
    )
    return informe(titulo, criterios(m, desarrollo, prueba))


if __name__ == "__main__":
    sys.exit(main())

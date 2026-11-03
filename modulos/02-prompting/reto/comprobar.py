"""Comprueba el reto del módulo 2: extrae los 15 avisos con tu prompt, tu esquema y tu rol, y
mide cada campo. Llama al modelo: unos 30 segundos con el de 1,5B y unos 3 minutos con el de 7B.

Uso: `uv run python modulos/02-prompting/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from curso_core.retos import Criterio, cargar, elegir, informe

AQUI = Path(__file__).resolve().parent
# Cuántos de los 15 correos tienen que estar bien en cada campo.
MINIMOS = {"servicio": 14, "hora_inicio": 14, "afecta_clientes": 14, "severidad": 10}
COMPLETOS = 10


def criterios(m, avisos: list, correos: list[dict]) -> list[Criterio]:
    """Los criterios a partir de los avisos extraídos (None si el modelo no dio uno válido)."""
    fallos = [m.campos_mal(a, c["esperado"]) for a, c in zip(avisos, correos, strict=True)]
    n = len(correos)
    resultado = []
    for campo, minimo in MINIMOS.items():
        bien = sum(campo not in f for f in fallos)
        malos = [str(c["id"]) for f, c in zip(fallos, correos, strict=True) if campo in f]
        detalle = f"{bien} de {n}" + (f" (mal: {', '.join(malos)})" if malos else "")
        resultado.append(Criterio(f"{campo}: al menos {minimo} de {n}", bien >= minimo, detalle))
    completos = sum(not f for f in fallos)
    resultado.append(
        Criterio(
            f"avisos enteros correctos: al menos {COMPLETOS} de {n}",
            completos >= COMPLETOS,
            f"{completos} de {n}",
        )
    )
    return resultado


def main() -> int:
    from curso_core import ClienteLLM

    ruta, _ = elegir(AQUI, "extractor.py", __doc__.splitlines()[0])
    m = cargar(ruta)
    cliente, correos = ClienteLLM(), m.correos()
    inicio = time.perf_counter()
    avisos = [m.extraer(cliente, c["texto"]) for c in correos]
    segundos = time.perf_counter() - inicio
    titulo = (
        f"Reto del módulo 2 · {ruta.relative_to(AQUI.parent).as_posix()}"
        f" · rol {m.ROL} · {segundos:.0f} s"
    )
    return informe(titulo, criterios(m, avisos, correos))


if __name__ == "__main__":
    sys.exit(main())

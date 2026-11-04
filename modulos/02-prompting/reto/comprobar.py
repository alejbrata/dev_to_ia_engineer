"""Comprueba el reto del módulo 2: extrae los avisos con tu prompt, tu esquema y tu rol, y mide
cada campo. Por defecto, con los 15 correos de desarrollo; con `--prueba`, con los 10 de prueba,
que se miran una vez, al final (lección 4.06). Llama al modelo: con los 15, unos 30 segundos
con el de 1,5B y unos 3 minutos con el de 7B.

Uso: `uv run python modulos/02-prompting/reto/comprobar.py [--solucion] [--prueba]`
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from curso_core.retos import Criterio, cargar, informe

AQUI = Path(__file__).resolve().parent
# Cuántos correos tienen que estar bien en cada campo. La severidad, la decisión difícil, pide
# menos. Los de prueba guardan la proporción de los de desarrollo, redondeando hacia abajo.
MINIMOS = {
    "desarrollo": {"servicio": 14, "hora_inicio": 14, "afecta_clientes": 14, "severidad": 10},
    "prueba": {"servicio": 9, "hora_inicio": 9, "afecta_clientes": 9, "severidad": 6},
}
COMPLETOS = {"desarrollo": 10, "prueba": 6}


def criterios(
    m, avisos: list, correos: list[dict], particion: str = "desarrollo"
) -> list[Criterio]:
    """Los criterios a partir de los avisos extraídos (None si el modelo no dio uno válido)."""
    fallos = [m.campos_mal(a, c["esperado"]) for a, c in zip(avisos, correos, strict=True)]
    n = len(correos)
    resultado = []
    for campo, minimo in MINIMOS[particion].items():
        bien = sum(campo not in f for f in fallos)
        malos = [str(c["id"]) for f, c in zip(fallos, correos, strict=True) if campo in f]
        detalle = f"{bien} de {n}" + (f" (mal: {', '.join(malos)})" if malos else "")
        resultado.append(
            Criterio(f"{particion}: {campo}, al menos {minimo} de {n}", bien >= minimo, detalle)
        )
    completos = sum(not f for f in fallos)
    resultado.append(
        Criterio(
            f"{particion}: avisos enteros correctos, al menos {COMPLETOS[particion]} de {n}",
            completos >= COMPLETOS[particion],
            f"{completos} de {n}",
        )
    )
    return resultado


def main() -> int:
    from curso_core import ClienteLLM

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--solucion", action="store_true", help="comprueba la solución")
    parser.add_argument("--prueba", action="store_true", help="usa los correos de prueba")
    args = parser.parse_args()
    ruta = AQUI / ("solucion" if args.solucion else "") / "extractor.py"
    particion = "prueba" if args.prueba else "desarrollo"
    m = cargar(ruta)
    cliente, correos = ClienteLLM(), m.correos(particion)
    inicio = time.perf_counter()
    avisos = [m.extraer(cliente, c["texto"]) for c in correos]
    segundos = time.perf_counter() - inicio
    titulo = (
        f"Reto del módulo 2 · {ruta.relative_to(AQUI.parent).as_posix()} · {particion}"
        f" · rol {m.ROL} · {segundos:.0f} s"
    )
    return informe(titulo, criterios(m, avisos, correos, particion))


if __name__ == "__main__":
    sys.exit(main())

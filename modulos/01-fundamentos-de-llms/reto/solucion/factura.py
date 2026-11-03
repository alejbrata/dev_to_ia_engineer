"""Solución del reto del módulo 1. Los cuatro cambios están marcados con «Arreglo».

La segunda semana, el asistente de soporte costó bastante más que la primera. Producto cree
que es por la campaña del día 4, que trajo mucho tráfico. `llamadas.jsonl` es una muestra del
log de esas dos semanas: una línea por llamada al modelo, con sus tokens y su latencia.

Uso: `uv run python modulos/01-fundamentos-de-llms/reto/solucion/factura.py`
Comprobar: `uv run python modulos/01-fundamentos-de-llms/reto/comprobar.py --solucion`
"""

from __future__ import annotations

import json
import math
import sys
import tomllib
from collections import defaultdict
from pathlib import Path
from statistics import mean

# La carpeta del reto, también desde solucion/: ahí están el log y los precios.
DATOS = next(p for p in Path(__file__).resolve().parents if p.name == "reto")
CAUSAS = (
    "más tráfico",
    "un modelo más caro",
    "respuestas más largas",
    "el contexto crece con cada turno",
)
# Arreglo 4: los tokens de entrada crecen con el turno desde el día 8, y antes no.
CAUSA = "el contexto crece con cada turno"


def cargar(ruta: Path = DATOS / "llamadas.jsonl") -> list[dict]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]


def precios(ruta: Path = DATOS / "precios.toml") -> dict[str, float]:
    with ruta.open("rb") as f:
        return tomllib.load(f)


def coste(llamada: dict, precios: dict[str, float]) -> float:
    """Lo que cuesta una llamada, en USD. Los precios van por millón de tokens."""
    # Arreglo 1: entrada y salida tienen precios distintos.
    entrada = llamada["tokens_entrada"] * precios["entrada"]
    return (entrada + llamada["tokens_salida"] * precios["salida"]) / 1_000_000


def p95(valores: list[float]) -> float:
    """El percentil 95 (por rango): el valor por debajo del cual queda el 95 % de los datos."""
    # Arreglo 2: un percentil se lee sobre los valores ordenados.
    return sorted(valores)[math.ceil(0.95 * len(valores)) - 1]


def por_dia(llamadas: list[dict], precios: dict[str, float]) -> dict[str, dict]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for llamada in llamadas:
        grupos[llamada["dia"]].append(llamada)
    dias = {}
    for dia, filas in sorted(grupos.items()):
        total = sum(coste(f, precios) for f in filas)
        dias[dia] = {
            "llamadas": len(filas),
            "coste": total,
            "coste_por_llamada": total / len(filas),
            "p95_ms": p95([f["ms"] for f in filas]),
        }
    return dias


def dia_del_cambio(dias: dict[str, dict], umbral: float = 1.3) -> str | None:
    """El primer día que se dispara frente a la media de los anteriores, o None."""
    orden = list(dias)
    for i in range(1, len(orden)):
        # Arreglo 3: el coste por llamada, no el total. El total sube con el tráfico (la
        # campaña del día 4) aunque cada llamada cueste lo mismo.
        anteriores = mean(dias[d]["coste_por_llamada"] for d in orden[:i])
        if dias[orden[i]]["coste_por_llamada"] > umbral * anteriores:
            return orden[i]
    return None


def entrada_por_turno(llamadas: list[dict]) -> dict[int, float]:
    """La media de tokens de entrada según el turno de la conversación."""
    grupos: dict[int, list[int]] = defaultdict(list)
    for llamada in llamadas:
        grupos[llamada["turno"]].append(llamada["tokens_entrada"])
    return {turno: mean(v) for turno, v in sorted(grupos.items())}


def main() -> int:
    llamadas, tarifa = cargar(), precios()
    dias = por_dia(llamadas, tarifa)
    print(f"{'día':12} {'llamadas':>9} {'coste':>9} {'por llamada':>12} {'p95':>8}")
    for dia, d in dias.items():
        print(
            f"{dia:12} {d['llamadas']:>9} {d['coste']:>8.3f}$ "
            f"{d['coste_por_llamada'] * 1000:>9.3f} m$ {d['p95_ms'] / 1000:>7.1f}s"
        )
    orden = list(dias)
    for nombre, semana in (("primera", orden[:7]), ("segunda", orden[7:])):
        total = sum(dias[d]["coste"] for d in semana)
        n = sum(dias[d]["llamadas"] for d in semana)
        print(f"semana {nombre}: {n} llamadas, {total:.2f} $")
    cambio = dia_del_cambio(dias)
    print(f"día del cambio: {cambio}")
    if cambio:
        antes = entrada_por_turno([f for f in llamadas if f["dia"] < cambio])
        despues = entrada_por_turno([f for f in llamadas if f["dia"] >= cambio])
        print("tokens de entrada por turno, antes y después del cambio:")
        for turno in antes:
            print(f"   turno {turno:2}: {antes[turno]:7.0f} {despues.get(turno, 0):7.0f}")
    print(f"causa: {CAUSA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

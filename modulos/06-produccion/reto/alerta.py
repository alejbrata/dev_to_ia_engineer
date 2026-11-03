"""Reto del módulo 6: la alerta de las 3:00.

La segunda noche, desde las 3:00, el asistente empezó a responder mal y nadie se enteró hasta
la mañana: no saltó ninguna alerta. La primera noche, en cambio, saltó una a la 1:00 y no era
nada grave. `peticiones.jsonl` tiene las peticiones de esas dos noches, sacadas de las trazas
(lección 02): latencia, errores, qué rol respondió, tokens enviados y procesados, y si la
respuesta fue una abstención.

Este script agrupa las peticiones en ventanas de 10 minutos, decide en cuáles salta la alerta
y dice la causa. Tiene fallos. `comprobar.py` dice qué criterios no cumple; arréglalo hasta que
los cumpla todos, y cambia `CAUSA` por la que expliquen los datos.

Uso: `uv run python modulos/06-produccion/reto/alerta.py`
Comprobar: `uv run python modulos/06-produccion/reto/comprobar.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# El log, también desde solucion/: está en la carpeta del reto.
DATOS = next(p for p in Path(__file__).resolve().parents if p.name == "reto")
VENTANA = 10  # minutos
CAUSAS = (
    "el modelo principal no responde y responde el de respaldo",
    "más tráfico del habitual",
    "el servidor del modelo recorta el contexto",
    "el modelo principal tarda más",
)
CAUSA = "más tráfico del habitual"  # cámbiala por la que expliquen los datos


def cargar(ruta: Path = DATOS / "peticiones.jsonl") -> list[dict]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]


def minuto(hora: str) -> int:
    h, m, _ = hora.split(":")
    return int(h) * 60 + int(m)


def ventanas(peticiones: list[dict], noche: int) -> list[dict]:
    """Las señales de cada ventana de 10 minutos de una noche."""
    grupos: dict[int, list[dict]] = {}
    for p in peticiones:
        if p["noche"] == noche:
            grupos.setdefault(minuto(p["hora"]) // VENTANA, []).append(p)
    resultado = []
    for i, ps in sorted(grupos.items()):
        n = len(ps)
        ms = sorted(p["ms"] for p in ps)
        resultado.append(
            {
                "inicio": f"{i * VENTANA // 60:02d}:{i * VENTANA % 60:02d}",
                "peticiones": n,
                "errores": sum(p["error"] for p in ps) / n,
                "abstenciones": sum(p["abstencion"] for p in ps) / n,
                "respaldo": sum(p["rol"] != "chat_grande" for p in ps) / n,
                "p95_ms": ms[min(n - 1, int(0.95 * n))],
            }
        )
    return resultado


def alerta(v: dict) -> bool:
    """Si la alerta salta en esta ventana."""
    return v["errores"] > 0.02


def main() -> int:
    peticiones = cargar()
    for noche in (1, 2):
        print(f"noche {noche}")
        print(f"   {'':5} {'pet.':>5} {'errores':>8} {'abstenc.':>9} {'respaldo':>9} {'p95':>7}")
        for v in ventanas(peticiones, noche):
            marca = "ALERTA" if alerta(v) else ""
            senales = f"{v['errores']:>8.0%} {v['abstenciones']:>9.0%} {v['respaldo']:>9.0%}"
            p95 = f"{v['p95_ms'] / 1000:>6.1f}s"
            print(f"   {v['inicio']} {v['peticiones']:>5} {senales} {p95} {marca}")
    print(f"causa: {CAUSA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

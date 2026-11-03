"""Solución del reto del módulo 6. Los tres cambios están marcados con «Arreglo».

La segunda noche, desde las 3:00, el asistente empezó a responder mal y nadie se enteró hasta
la mañana: no saltó ninguna alerta. La primera noche, en cambio, saltó una a la 1:00 y no era
nada grave. `peticiones.jsonl` tiene las peticiones de esas dos noches, sacadas de las trazas
(lección 02): latencia, errores, qué rol respondió, tokens enviados y procesados, y si la
respuesta fue una abstención.

Uso: `uv run python modulos/06-produccion/reto/solucion/alerta.py`
Comprobar: `uv run python modulos/06-produccion/reto/comprobar.py --solucion`
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
# Arreglo 3: desde las 3:00, el servidor procesa como mucho 1.024 tokens de prompts de unos 1.500.
CAUSA = "el servidor del modelo recorta el contexto"


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
                # Arreglo 1: la señal que deja la traza del recorte (lección 1.02): el servidor
                # procesa menos tokens de los que le mandas. Sin errores y sin más latencia.
                "recortadas": sum(
                    not p["error"] and p["tokens_procesados"] < p["tokens_enviados"] for p in ps
                )
                / n,
            }
        )
    return resultado


def alerta(v: dict) -> bool:
    """Si la alerta salta en esta ventana."""
    # Arreglo 2: con unas 30 peticiones por ventana, un solo error es un 3 %: la alerta de
    # errores saltaba por ruido y nadie la miraba. Esta mira lo que falla de verdad aquí. Una
    # alerta de errores sigue haciendo falta, con un umbral y una ventana que no salten por
    # un error suelto (lección 03).
    return v["recortadas"] > 0.10


def main() -> int:
    peticiones = cargar()
    for noche in (1, 2):
        print(f"noche {noche}")
        print(
            f"   {'':5} {'pet.':>5} {'errores':>8} {'abstenc.':>9} {'respaldo':>9} {'p95':>7}"
            f" {'recort.':>8}"
        )
        for v in ventanas(peticiones, noche):
            marca = "ALERTA" if alerta(v) else ""
            senales = f"{v['errores']:>8.0%} {v['abstenciones']:>9.0%} {v['respaldo']:>9.0%}"
            p95 = f"{v['p95_ms'] / 1000:>6.1f}s"
            print(
                f"   {v['inicio']} {v['peticiones']:>5} {senales} {p95}"
                f" {v['recortadas']:>8.0%} {marca}"
            )
    print(f"causa: {CAUSA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

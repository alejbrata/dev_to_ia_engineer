"""Genera `peticiones.jsonl`, las peticiones de dos noches del asistente para el reto del módulo 6.

Una línea por petición, con lo que dejan sus trazas (lección 02): la hora, la latencia, si
acabó en error, qué rol respondió, los tokens que el cliente mandó, los que el servidor del
modelo procesó (`gen_ai.usage.input_tokens`) y si la respuesta fue una abstención.

Lo que pasa (no lo leas antes de hacer el reto): la primera noche es normal, salvo un pico de
tráfico entre la 1:00 y la 1:20 que satura un poco el servicio (algo más de latencia y algún
error). La segunda, desde las 3:00, el servidor del modelo principal arranca con un contexto de
1.024 tokens y recorta el principio de los prompts sin avisar (lección 1.02). La semilla es
fija.

Uso: `uv run python modulos/06-produccion/reto/generar_peticiones.py`
"""

from __future__ import annotations

import json
import random
from pathlib import Path

AQUI = Path(__file__).resolve().parent
HORAS = 6  # de 0:00 a 6:00
CONTEXTO_RECORTADO = 1024


def peticiones(semilla: int = 3) -> list[dict]:
    azar = random.Random(semilla)
    filas = []
    for noche in (1, 2):
        for minuto in range(HORAS * 60):
            pico = noche == 1 and 60 <= minuto < 80
            recorte = noche == 2 and minuto >= 180
            n = azar.randint(1, 5) if not pico else azar.randint(8, 12)
            for _ in range(n):
                enviados = max(600, int(azar.gauss(1500, 300)))
                procesados = min(enviados, CONTEXTO_RECORTADO) if recorte else enviados
                # Sin el principio del prompt (las reglas y los primeros fragmentos), el modelo
                # se abstiene mucho más, y genera menos.
                abstencion = azar.random() < (0.55 if recorte else 0.12)
                error = azar.random() < (0.03 if pico else 0.004)
                ms = int(azar.gauss(9000 if recorte else 11500, 2500) * (1.3 if pico else 1))
                filas.append(
                    {
                        "noche": noche,
                        "hora": f"{minuto // 60:02d}:{minuto % 60:02d}:{azar.randint(0, 59):02d}",
                        "ms": max(1500, ms),
                        "error": error,
                        "rol": "chat" if azar.random() < 0.01 else "chat_grande",
                        "tokens_enviados": enviados,
                        "tokens_procesados": 0 if error else procesados,
                        "abstencion": False if error else abstencion,
                    }
                )
    return sorted(filas, key=lambda f: (f["noche"], f["hora"]))


def main() -> None:
    filas = peticiones()
    with (AQUI / "peticiones.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for fila in filas:
            f.write(json.dumps(fila) + "\n")
    print(f"{len(filas)} peticiones en {AQUI / 'peticiones.jsonl'}")


if __name__ == "__main__":
    main()

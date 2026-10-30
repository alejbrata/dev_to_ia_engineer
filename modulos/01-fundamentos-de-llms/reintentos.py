"""Reintentos con backoff frente a un límite de uso (429), medidos.

Arranca el simulador (3 peticiones cada 5 segundos) y le lanza 8 peticiones
seguidas, primero con la cabecera Retry-After y después sin ella. Muestra cuántos
intentos necesitó cada una y cuánto tardó, y el resumen de las trazas.

Uso: `uv run python modulos/01-fundamentos-de-llms/reintentos.py`
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import simulador
from curso_core import ClienteLLM
from curso_core import config as cfg
from curso_core.metrics import resumir
from curso_core.tracing import leer

ROL = "simulador"
PETICIONES = 8


def ronda(config: cfg.Config, trazas: Path, retry_after: bool, puerto: int) -> None:
    servidor = simulador.arrancar_en_segundo_plano(
        puerto=puerto, limite=3, ventana=5, retry_after=retry_after
    )
    config.providers[config.roles[ROL].provider].base_url = f"http://127.0.0.1:{puerto}/v1"
    cliente = ClienteLLM(config, trazas=trazas, reintentos=4)
    titulo = "con Retry-After" if retry_after else "sin Retry-After (backoff exponencial)"
    print(f"\n{PETICIONES} peticiones seguidas, {titulo}")
    for n in range(1, PETICIONES + 1):
        r = cliente.chat(f"Petición {n}", rol=ROL)
        print(f"  petición {n}: {r.intentos} intento(s), {r.latencia_s:5.2f} s")
    servidor.shutdown()

    resumen = resumir(leer(trazas))
    print(
        f"  resumen: {resumen.llamadas} llamadas, {resumen.errores} errores, "
        f"{resumen.reintentos} reintentos, "
        f"p50 {resumen.latencia_p50_s:.2f} s, p95 {resumen.latencia_p95_s:.2f} s"
    )


def main() -> int:
    config = cfg.cargar()
    with TemporaryDirectory() as carpeta:
        ronda(config, Path(carpeta) / "con.jsonl", retry_after=True, puerto=8099)
        ronda(config, Path(carpeta) / "sin.jsonl", retry_after=False, puerto=8098)
    return 0


if __name__ == "__main__":
    sys.exit(main())

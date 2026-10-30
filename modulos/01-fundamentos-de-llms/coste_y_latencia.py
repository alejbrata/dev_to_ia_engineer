"""Coste y latencia de una carga real, medidos con las trazas de curso_core.

1. Lanza 20 peticiones al modelo local y resume latencia (p50, p95), tokens y velocidad.
2. Con los tokens medidos, proyecta el coste de un millón de peticiones en un proveedor
   (rol `remoto`) usando el precio de `config/models.toml` y el que publica hoy la API
   de Hugging Face, y lo compara con el tiempo de máquina que costaría en local.

Uso: `uv run python modulos/01-fundamentos-de-llms/coste_y_latencia.py`
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
from curso_core import ClienteLLM, Opciones
from curso_core import config as cfg
from curso_core.metrics import Resumen, resumir
from curso_core.tracing import leer

ROUTER = "https://router.huggingface.co/v1/models"
PETICIONES_PROYECTADAS = 1_000_000

TEMAS = [
    "una cola de mensajes",
    "una caché",
    "un índice de base de datos",
    "un balanceador de carga",
]
PLANTILLAS = [
    "Define {} en una frase.",
    "Explica en tres frases qué es {} y cuándo usarlo.",
    "Da dos ventajas y un inconveniente de usar {}.",
    "Pon un ejemplo de uso de {} en una aplicación web.",
    "¿Qué métrica vigilarías en {}? Responde en una frase.",
]
PROMPTS = [p.format(t) for t in TEMAS for p in PLANTILLAS]  # 20 peticiones


def miles(numero: float) -> str:
    """Número entero con punto de miles, a la española: 1881 -> '1.881'."""
    return f"{numero:,.0f}".replace(",", ".")


def coste_por_peticion(entrada: float, salida: float, precio: cfg.Precio) -> float:
    """USD de una petición media; el precio va en USD por millón de tokens."""
    return (entrada * precio.entrada + salida * precio.salida) / 1_000_000


def precio_publicado(modelo: str) -> cfg.Precio | None:
    """Precio más barato que publica hoy la API de Hugging Face para ese modelo."""
    try:
        datos = httpx.get(ROUTER, timeout=20).json()["data"]
    except httpx.HTTPError:
        return None
    ficha = next((m for m in datos if m["id"] == modelo), None)
    precios = [p["pricing"] for p in (ficha or {}).get("providers", []) if p.get("pricing")]
    if not precios:
        return None
    barato = min(precios, key=lambda p: p["input"] + p["output"])
    return cfg.Precio(entrada=barato["input"], salida=barato["output"])


def medir(cliente: ClienteLLM, trazas: Path) -> Resumen:
    print(f"1. {len(PROMPTS)} peticiones al modelo local")
    for n, prompt in enumerate(PROMPTS, 1):
        r = cliente.chat(prompt, opciones=Opciones(temperatura=0, max_tokens=150))
        print(f"  {n:2}. {r.latencia_s:5.2f} s · {r.tokens_entrada:3} + {r.tokens_salida:3} tokens")
    resumen = resumir(leer(trazas))
    trazas_buenas = [t for t in leer(trazas) if t.ok]
    velocidad = resumen.tokens_salida / sum(t.latencia_s for t in trazas_buenas)
    print(
        f"\n  p50 {resumen.latencia_p50_s:.2f} s · p95 {resumen.latencia_p95_s:.2f} s · "
        f"{velocidad:.1f} tokens/s · errores {resumen.errores}"
    )
    return resumen


def proyectar(config: cfg.Config, resumen: Resumen) -> None:
    entrada = resumen.tokens_entrada / resumen.llamadas
    salida = resumen.tokens_salida / resumen.llamadas
    millones = PETICIONES_PROYECTADAS / 1_000_000
    print(f"\n2. Proyección para {miles(PETICIONES_PROYECTADAS)} peticiones")
    print(f"  petición media: {entrada:.0f} tokens de entrada y {salida:.0f} de salida")

    horas = resumen.latencia_p50_s * PETICIONES_PROYECTADAS / 3600
    print(f"  local: 0 $ por token, pero ~{miles(horas)} horas de esta máquina en serie")

    nombre, _, modelo = config.resolver("remoto")
    for origen, precio in [
        ("models.toml", config.precio(nombre, modelo)),
        ("publicado hoy", precio_publicado(modelo)),
    ]:
        if precio is None:
            print(f"  {modelo} ({origen}): sin precio disponible")
            continue
        total = coste_por_peticion(entrada, salida, precio) * PETICIONES_PROYECTADAS
        print(
            f"  {modelo} ({origen}): {precio.entrada} $ / {precio.salida} $ por millón "
            f"-> {total:,.2f} $ por {millones:g} millón de peticiones"
        )


def main() -> int:
    config = cfg.cargar()
    with TemporaryDirectory() as carpeta:
        trazas = Path(carpeta) / "carga.jsonl"
        resumen = medir(ClienteLLM(config, trazas=trazas), trazas)
    proyectar(config, resumen)
    return 0


if __name__ == "__main__":
    sys.exit(main())

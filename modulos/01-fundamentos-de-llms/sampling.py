"""Sampling: temperatura, top_p y semilla, medidos.

1. Cómo cambia la temperatura las probabilidades reales del siguiente token.
2. Cuántas respuestas distintas salen al repetir la misma petición con cada ajuste.
3. Si una semilla fija hace la salida reproducible, también tras recargar el modelo.

Uso: `uv run python modulos/01-fundamentos-de-llms/sampling.py [repeticiones]`
"""

from __future__ import annotations

import math
import sys
from collections import Counter

import httpx
from curso_core import ClienteLLM, Opciones
from curso_core import config as cfg

PROMPT_COLOR = "Completa con una sola palabra: el cielo despejado es de color"
PROMPT_NOMBRE = "Inventa un nombre para una cafetería. Responde solo con el nombre, sin comillas."
REPETICIONES = 10
MAX_TOKENS = 15

AJUSTES = {
    "T=0": Opciones(temperatura=0),
    "T=0.7": Opciones(temperatura=0.7),
    "T=1.5": Opciones(temperatura=1.5),
    "T=1.5, top_p=0.3": Opciones(temperatura=1.5, top_p=0.3),
    "T=0.8, semilla=42": Opciones(temperatura=0.8, semilla=42),
}


def reescalar(probabilidades: dict[str, float], temperatura: float) -> dict[str, float]:
    """Aplica una temperatura a una distribución: p^(1/T), normalizado.

    Equivale a dividir los logits por T antes del softmax. Con T=0, todo para el más probable.
    """
    if temperatura == 0:
        mejor = max(probabilidades, key=probabilidades.get)
        return {t: float(t == mejor) for t in probabilidades}
    pesos = {t: math.exp(math.log(p) / temperatura) for t, p in probabilidades.items()}
    total = sum(pesos.values())
    return {t: w / total for t, w in pesos.items()}


def barra(probabilidad: float, ancho: int = 30) -> str:
    return "#" * round(probabilidad * ancho)


def distribucion(cliente: ClienteLLM) -> None:
    print(f"1. Probabilidades del primer token\n> {PROMPT_COLOR}\n")
    r = cliente.chat(PROMPT_COLOR, opciones=Opciones(temperatura=0, max_tokens=1, alternativas=5))
    originales = {a.token: a.probabilidad for a in r.tokens[0].alternativas}
    for temperatura in (0.3, 1.0, 1.5):
        print(f"   T={temperatura}")
        for token, p in reescalar(originales, temperatura).items():
            print(f"   {token!r:>8} {p:6.1%} {barra(p)}")
    print("   (reescaladas sobre los 5 tokens más probables)\n")


def repeticiones(cliente: ClienteLLM, n: int) -> None:
    print(f"2. {n} repeticiones de la misma petición\n> {PROMPT_NOMBRE}\n")
    for nombre, opciones in AJUSTES.items():
        opciones = opciones.model_copy(update={"max_tokens": MAX_TOKENS})
        respuestas = Counter(
            cliente.chat(PROMPT_NOMBRE, opciones=opciones).texto.strip() for _ in range(n)
        )
        ejemplos = ", ".join(f"{t!r}×{c}" for t, c in respuestas.most_common(3))
        print(f"   {nombre:18} {len(respuestas):2} de {n} distintas · {ejemplos}")
    print()


def descargar_modelo(base_url: str, modelo: str) -> None:
    """Pide a Ollama que descargue el modelo de memoria (keep_alive=0)."""
    httpx.post(f"{base_url}/api/generate", json={"model": modelo, "keep_alive": 0}, timeout=60)


def reproducibilidad(cliente: ClienteLLM, base_url: str, modelo: str) -> None:
    print("3. Semilla fija (T=0.8, semilla=42), recargando el modelo antes de cada ronda\n")
    opciones = AJUSTES["T=0.8, semilla=42"].model_copy(update={"max_tokens": MAX_TOKENS})
    for ronda in range(1, 4):
        descargar_modelo(base_url, modelo)
        salidas = [cliente.chat(PROMPT_NOMBRE, opciones=opciones).texto.strip() for _ in range(4)]
        print(f"   ronda {ronda}: {salidas}")


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else REPETICIONES
    config = cfg.cargar()
    _, proveedor, modelo = config.resolver("chat")
    cliente = ClienteLLM(config)

    distribucion(cliente)
    repeticiones(cliente, n)
    if proveedor.tipo == "ollama":
        reproducibilidad(cliente, proveedor.base_url, modelo)
    return 0


if __name__ == "__main__":
    sys.exit(main())

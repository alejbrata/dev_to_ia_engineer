"""Primer "hola mundo" con un LLM servido en local por Ollama.

Lee el modelo del rol `chat` en `config/models.toml`, le manda una pregunta por la
API HTTP de Ollama e imprime la respuesta junto con sus métricas básicas.

Uso: `uv run python modulos/00-introduccion/hola_mundo.py "tu pregunta"`
"""

from __future__ import annotations

import sys
import time
import tomllib
from pathlib import Path

import httpx
from pydantic import BaseModel

RAIZ = Path(__file__).resolve().parents[2]
PREGUNTA_POR_DEFECTO = "Explica en una sola frase qué es un modelo de lenguaje."
NS_POR_SEGUNDO = 1_000_000_000


class Mensaje(BaseModel):
    role: str
    content: str


class RespuestaOllama(BaseModel):
    """Los campos de la respuesta de /api/chat que usamos. Duraciones en nanosegundos."""

    model: str
    message: Mensaje
    prompt_eval_count: int = 0
    eval_count: int = 0
    load_duration: int = 0
    total_duration: int = 0


class Config(BaseModel):
    base_url: str
    modelo: str


def leer_config(ruta: Path) -> Config:
    with ruta.open("rb") as f:
        datos = tomllib.load(f)
    chat = datos["roles"]["chat"]
    proveedor = datos["providers"][chat["provider"]]
    return Config(base_url=proveedor["base_url"], modelo=chat["model"])


def preguntar(cliente: httpx.Client, modelo: str, pregunta: str) -> tuple[RespuestaOllama, float]:
    """Devuelve la respuesta y la latencia medida desde el cliente, en segundos."""
    inicio = time.perf_counter()
    r = cliente.post(
        "/api/chat",
        json={
            "model": modelo,
            "messages": [{"role": "user", "content": pregunta}],
            "stream": False,
        },
    )
    latencia = time.perf_counter() - inicio
    r.raise_for_status()
    return RespuestaOllama.model_validate(r.json()), latencia


def main() -> int:
    pregunta = " ".join(sys.argv[1:]) or PREGUNTA_POR_DEFECTO
    config = leer_config(RAIZ / "config" / "models.toml")

    with httpx.Client(base_url=config.base_url, timeout=120) as cliente:
        try:
            respuesta, latencia = preguntar(cliente, config.modelo, pregunta)
        except httpx.ConnectError:
            print(f"No hay nadie escuchando en {config.base_url}. ¿Está Ollama arrancado?")
            return 1
        except httpx.HTTPStatusError as e:
            # El mensaje de la excepción solo trae el código; el motivo está en el cuerpo.
            print(f"Ollama respondió {e.response.status_code}: {e.response.text}")
            return 1

    print(f"> {pregunta}\n")
    print(respuesta.message.content.strip())
    print(
        f"\n[{respuesta.model}] "
        f"tokens entrada={respuesta.prompt_eval_count} salida={respuesta.eval_count} · "
        f"latencia={latencia:.2f}s "
        f"(carga del modelo {respuesta.load_duration / NS_POR_SEGUNDO:.2f}s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

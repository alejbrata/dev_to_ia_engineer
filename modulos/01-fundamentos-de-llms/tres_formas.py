"""La misma llamada de tres formas: HTTP a mano, SDK de OpenAI y curso_core.

Las tres hablan con el mismo modelo local. Compara cuánto código pide cada una y qué
te devuelve sin trabajo extra.

Uso: `uv run python modulos/01-fundamentos-de-llms/tres_formas.py`
"""

from __future__ import annotations

import sys

import httpx
from curso_core import ClienteLLM, Mensaje, Opciones
from curso_core import config as cfg
from openai import OpenAI

SISTEMA = "Eres un asistente técnico. Responde en una sola frase, en español."
PREGUNTA = "¿Para qué sirve un balanceador de carga?"


def con_http(base_url: str, modelo: str) -> tuple[str, int, int]:
    """1. HTTP a mano contra la API nativa de Ollama."""
    r = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": modelo,
            "messages": [
                {"role": "system", "content": SISTEMA},
                {"role": "user", "content": PREGUNTA},
            ],
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=120,
    )
    r.raise_for_status()
    datos = r.json()
    return datos["message"]["content"], datos["prompt_eval_count"], datos["eval_count"]


def con_sdk(base_url: str, modelo: str) -> tuple[str, int, int]:
    """2. SDK de OpenAI contra la API compatible de Ollama (/v1)."""
    # Ollama no comprueba la clave, pero el SDK exige una.
    cliente = OpenAI(base_url=base_url, api_key="ollama")
    r = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": PREGUNTA},
        ],
        temperature=0,
    )
    return r.choices[0].message.content, r.usage.prompt_tokens, r.usage.completion_tokens


def con_curso_core(rol: str) -> tuple[str, int, int]:
    """3. curso_core: el rol decide proveedor y modelo; la traza y el coste van incluidos."""
    r = ClienteLLM().chat(
        [Mensaje(role="system", content=SISTEMA), Mensaje(role="user", content=PREGUNTA)],
        rol=rol,
        opciones=Opciones(temperatura=0),
    )
    return r.texto, r.tokens_entrada, r.tokens_salida


def main() -> int:
    config = cfg.cargar()
    _, nativo, modelo = config.resolver("chat")
    _, compatible, modelo_compatible = config.resolver("chat_compatible")

    print(f"> {PREGUNTA}\n")
    formas = [
        ("1. HTTP a mano (API nativa)", lambda: con_http(nativo.base_url, modelo)),
        ("2. SDK de OpenAI (API /v1)", lambda: con_sdk(compatible.base_url, modelo_compatible)),
        ("3. curso_core, rol chat", lambda: con_curso_core("chat")),
        ("3. curso_core, rol chat_compatible", lambda: con_curso_core("chat_compatible")),
    ]
    for nombre, llamar in formas:
        texto, entrada, salida = llamar()
        print(f"[{nombre}] {entrada} tokens de entrada, {salida} de salida")
        print(f"   {texto.strip()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Graba medidas reales del modelo del curso para los componentes interactivos de la web.

Escribe site/src/data/medidas.json con:

- el modelo y su repositorio en Hugging Face (para el visor de tokens);
- las probabilidades reales del primer token de una pregunta (deslizador de temperatura);
- dos respuestas en streaming con la marca de tiempo de cada fragmento (portada y
  repetición del streaming).

Necesita Ollama arrancado con el modelo del rol `chat`. Uso:
`uv run python scripts/datos_web.py`
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from curso_core import ClienteLLM, Opciones
from curso_core import config as cfg

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "site" / "src" / "data" / "medidas.json"

PROMPT_TEMPERATURA = "Completa con una sola palabra: el cielo despejado es de color"
PROMPT_PORTADA = "Explica en una sola frase qué es un modelo de lenguaje."
PROMPT_STREAMING = "Explica en cuatro frases qué es una cola de mensajes."


def grabar_stream(cliente: ClienteLLM, prompt: str) -> dict:
    """Respuesta en streaming con el instante (s desde el inicio) de cada fragmento."""
    inicio = time.perf_counter()
    flujo = cliente.chat_stream(prompt, opciones=Opciones(temperatura=0))
    fragmentos = [{"t": round(time.perf_counter() - inicio, 3), "texto": texto} for texto in flujo]
    r = flujo.respuesta
    return {
        "prompt": prompt,
        "fragmentos": fragmentos,
        "primer_token_s": round(r.primer_token_s, 3),
        "total_s": round(r.latencia_s, 3),
        "tokens_entrada": r.tokens_entrada,
        "tokens_salida": r.tokens_salida,
        "coste_usd": r.coste_usd,
    }


def main() -> None:
    config = cfg.cargar()
    _, _, modelo = config.resolver("chat")
    cliente = ClienteLLM(config)

    r = cliente.chat(
        PROMPT_TEMPERATURA, opciones=Opciones(temperatura=0, max_tokens=1, alternativas=5)
    )
    alternativas = [
        {"token": a.token, "probabilidad": round(a.probabilidad, 4)}
        for a in r.tokens[0].alternativas
    ]

    datos = {
        "revisado": date.today().strftime("%Y-%m"),
        "modelo": modelo,
        "hf_repo": config.roles["chat"].hf_repo,
        "temperatura": {"prompt": PROMPT_TEMPERATURA, "alternativas": alternativas},
        "portada": grabar_stream(cliente, PROMPT_PORTADA),
        "streaming": grabar_stream(cliente, PROMPT_STREAMING),
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Escrito {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()

"""Cómo ve el texto un LLM: tokens.

Trocea textos con el tokenizador real del modelo del rol `chat` (descargado de
Hugging Face) y compara lo que cuesta cada uno en tokens. Al final, compara los
tokens de una pregunta con los que el servidor dice haber procesado.

Uso: `uv run python modulos/01-fundamentos-de-llms/tokens.py ["texto propio"]`
"""

from __future__ import annotations

import os
import sys

# En Windows sin modo desarrollador, huggingface_hub avisa de que no puede usar enlaces
# simbólicos en su caché. Funciona igual (ocupa algo más de disco), así que lo silenciamos.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from curso_core import ClienteLLM, Opciones  # noqa: E402
from curso_core import config as cfg  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

EJEMPLOS = [
    ("español", "Explica en una sola frase qué es un modelo de lenguaje."),
    ("inglés", "Explain in a single sentence what a language model is."),
    ("palabras largas", "El ferrocarril metropolitano funciona ininterrumpidamente."),
    ("números", "1234567 + 89 = 1234656"),
    ("código", "def suma(a, b): return a + b"),
]


def trozos(texto: str, offsets: list[tuple[int, int]]) -> list[str]:
    """El fragmento de texto original que corresponde a cada token."""
    return [texto[inicio:fin] for inicio, fin in offsets]


def tokens_por_palabra(texto: str, n_tokens: int) -> float:
    return n_tokens / max(1, len(texto.split()))


def mostrar(tokenizer: Tokenizer, etiqueta: str, texto: str) -> int:
    codificado = tokenizer.encode(texto)
    n = len(codificado.ids)
    print(f"[{etiqueta}] {len(texto.split())} palabras -> {n} tokens", end=" ")
    print(f"({tokens_por_palabra(texto, n):.2f} tokens/palabra)")
    print("   " + "|".join(trozos(texto, codificado.offsets)))
    return n


def main() -> int:
    config = cfg.cargar()
    _, _, modelo = config.resolver("chat")
    repo = config.roles["chat"].hf_repo
    if not repo:
        print("El rol chat no tiene hf_repo en config/models.toml: no sé qué tokenizador usar.")
        return 1

    print(f"Tokenizador de {repo}\n")
    tokenizer = Tokenizer.from_pretrained(repo)

    ejemplos = [("tu texto", " ".join(sys.argv[1:]))] if len(sys.argv) > 1 else EJEMPLOS
    for etiqueta, texto in ejemplos:
        mostrar(tokenizer, etiqueta, texto)

    # Lo que cuenta el servidor: pedimos un solo token de salida para no esperar.
    pregunta = ejemplos[0][1]
    propios = len(tokenizer.encode(pregunta).ids)
    servidor = ClienteLLM().chat(pregunta, opciones=Opciones(max_tokens=1)).tokens_entrada
    print(f"\nTu pregunta: {propios} tokens. El servidor ({modelo}) procesó {servidor}.")
    print(f"Diferencia: {servidor - propios} tokens que no escribiste tú.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

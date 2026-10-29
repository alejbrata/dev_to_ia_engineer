"""Qué pasa cuando el prompt no cabe en la ventana de contexto.

Esconde un dato (un código de acceso) en un texto largo y pregunta por él en tres
casos: con el dato al principio y al final usando el contexto por defecto, y con el
dato al principio ampliando el contexto. Compara los tokens que mandas con los que
el servidor dice haber procesado.

Solo para Ollama: el tamaño del contexto y `/api/ps` son específicos suyos.

Uso: `uv run python modulos/01-fundamentos-de-llms/contexto.py [párrafos]`
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import httpx  # noqa: E402
from curso_core import ClienteLLM, Opciones  # noqa: E402
from curso_core import config as cfg  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

CODIGO = "7391"
DATO = f"Dato importante: el código de acceso al servidor de pruebas es {CODIGO}."
PREGUNTA = (
    "Pregunta: ¿cuál es el código de acceso al servidor de pruebas? Responde solo con el número."
)
PARRAFOS = 190
CONTEXTO_AMPLIADO = 8192


class Caso(BaseModel):
    nombre: str
    dato_al_final: bool
    contexto: int | None


CASOS = [
    Caso(nombre="dato al principio, contexto por defecto", dato_al_final=False, contexto=None),
    Caso(nombre="dato al final, contexto por defecto", dato_al_final=True, contexto=None),
    Caso(
        nombre=f"dato al principio, contexto {CONTEXTO_AMPLIADO}",
        dato_al_final=False,
        contexto=CONTEXTO_AMPLIADO,
    ),
]


def relleno(parrafos: int) -> str:
    return " ".join(
        f"Párrafo {i}: el equipo revisó los registros del sistema y no encontró "
        "incidencias relevantes en el turno de noche."
        for i in range(1, parrafos + 1)
    )


def construir_prompt(parrafos: int, dato_al_final: bool) -> str:
    partes = [relleno(parrafos), DATO] if dato_al_final else [DATO, relleno(parrafos)]
    return "\n\n".join([*partes, PREGUNTA])


def recortado(tokens_texto: int, tokens_procesados: int) -> bool:
    """El servidor procesó menos tokens de los que tiene tu texto: ha descartado parte."""
    return tokens_procesados < tokens_texto


def modelo_cargado(base_url: str) -> tuple[int, float]:
    """Contexto y memoria (GB) del modelo cargado ahora en Ollama."""
    [modelo, *_] = httpx.get(f"{base_url}/api/ps", timeout=10).json()["models"]
    return modelo["context_length"], modelo["size"] / 1e9


def main() -> int:
    parrafos = int(sys.argv[1]) if len(sys.argv) > 1 else PARRAFOS
    config = cfg.cargar()
    _, proveedor, modelo = config.resolver("chat")
    if proveedor.tipo != "ollama":
        print("Esta práctica necesita que el rol chat use Ollama.")
        return 1
    tokenizer = Tokenizer.from_pretrained(config.roles["chat"].hf_repo)
    cliente = ClienteLLM(config)

    for caso in CASOS:
        prompt = construir_prompt(parrafos, caso.dato_al_final)
        tokens_texto = len(tokenizer.encode(prompt).ids)
        r = cliente.chat(prompt, opciones=Opciones(temperatura=0, contexto=caso.contexto))
        contexto, memoria = modelo_cargado(proveedor.base_url)
        acierta = CODIGO in r.texto

        print(f"\n[{caso.nombre}]")
        print(f"  tu texto: {tokens_texto} tokens · procesados: {r.tokens_entrada}", end="")
        print("  <- RECORTADO" if recortado(tokens_texto, r.tokens_entrada) else "")
        print(f"  respuesta: {r.texto.strip()!r} ({'acierta' if acierta else 'FALLA'})")
        print(f"  latencia: {r.latencia_s:.1f} s · contexto {contexto} · memoria {memoria:.2f} GB")
    print(f"\nModelo: {modelo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

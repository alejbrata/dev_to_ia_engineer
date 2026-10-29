"""Errores reales de una API de modelos: autenticación, modelo, saldo y timeout.

Llama a Hugging Face Inference Providers (rol `remoto`) en varios escenarios y
muestra el código HTTP y el motivo que devuelve el servidor. Termina con un timeout
contra el modelo local.

Las llamadas a Hugging Face necesitan HF_TOKEN en .env. Si tu cuenta tiene créditos,
la primera llamada funcionará y costará una fracción de céntimo.

Uso: `uv run python modulos/01-fundamentos-de-llms/errores_api.py`
"""

from __future__ import annotations

import os
import sys

from curso_core import ClienteLLM, ErrorLLM, Opciones
from curso_core import config as cfg

OPCIONES = Opciones(max_tokens=5)
MODELO_INEXISTENTE = "modelo/que-no-existe"


def probar(nombre: str, llamar) -> None:
    print(f"[{nombre}]")
    try:
        r = llamar()
        print(f"   OK: {r.texto.strip()!r} ({r.tokens_entrada}+{r.tokens_salida} tokens)\n")
    except ErrorLLM as e:
        print(f"   status: {e.status} · intentos: {e.intentos}")
        print(f"   motivo: {e.cuerpo or e}\n")


def con_modelo(config: cfg.Config, modelo: str) -> cfg.Config:
    """Copia de la configuración con otro modelo en el rol `remoto`."""
    copia = config.model_copy(deep=True)
    copia.roles["remoto"].model = modelo
    return copia


def main() -> int:
    config = cfg.cargar()
    clave = config.providers["huggingface"].api_key_env

    probar("tu token", lambda: ClienteLLM(config).chat("Di hola.", rol="remoto", opciones=OPCIONES))

    probar(
        "modelo que no existe",
        lambda: ClienteLLM(con_modelo(config, MODELO_INEXISTENTE)).chat(
            "Di hola.", rol="remoto", opciones=OPCIONES
        ),
    )

    original = os.environ.get(clave)
    os.environ[clave] = "hf_token_inventado"
    try:
        probar(
            "token inválido",
            lambda: ClienteLLM(config).chat("Di hola.", rol="remoto", opciones=OPCIONES),
        )
    finally:
        if original is None:
            os.environ.pop(clave, None)
        else:
            os.environ[clave] = original

    # Un timeout de medio segundo para una respuesta larga del modelo local.
    probar(
        "timeout",
        lambda: ClienteLLM(config, timeout=0.5, reintentos=1).chat(
            "Escribe un párrafo largo sobre bases de datos.", opciones=Opciones(temperatura=0)
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

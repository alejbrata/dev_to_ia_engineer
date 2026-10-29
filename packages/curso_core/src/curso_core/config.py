"""Configuración de modelos, proveedores y precios, leída de `config/models.toml`."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

FICHERO = Path("config") / "models.toml"


class Proveedor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Dialecto de la API: el nativo de Ollama o el compatible con OpenAI,
    # que hablan OpenAI, Hugging Face, vLLM, llama.cpp y muchos otros.
    tipo: Literal["ollama", "openai"]
    base_url: str
    api_key_env: str | None = None


class Rol(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    # Repositorio del modelo en el Hub de Hugging Face: su ficha y su tokenizador.
    hf_repo: str | None = None


class Precio(BaseModel):
    """Precio en USD por millón de tokens."""

    model_config = ConfigDict(extra="forbid")

    entrada: float
    salida: float


class Config(BaseModel):
    roles: dict[str, Rol]
    providers: dict[str, Proveedor] = {}
    # Clave: "<proveedor>/<modelo>".
    precios: dict[str, Precio] = {}

    def resolver(self, rol: str) -> tuple[str, Proveedor, str]:
        """Devuelve (nombre del proveedor, proveedor, modelo) para un rol."""
        if rol not in self.roles:
            raise KeyError(f"El rol '{rol}' no está en models.toml")
        datos = self.roles[rol]
        if not datos.provider or not datos.model:
            raise ValueError(f"El rol '{rol}' no tiene proveedor y modelo en models.toml")
        if datos.provider not in self.providers:
            raise KeyError(f"El proveedor '{datos.provider}' no está en models.toml")
        return datos.provider, self.providers[datos.provider], datos.model

    def precio(self, proveedor: str, modelo: str) -> Precio | None:
        return self.precios.get(f"{proveedor}/{modelo}")


def buscar_fichero(desde: Path | None = None) -> Path:
    """Busca `config/models.toml` subiendo desde `desde` (o el directorio actual).

    La variable de entorno `CURSO_CONFIG` tiene prioridad.
    """
    if ruta := os.environ.get("CURSO_CONFIG"):
        return Path(ruta)
    actual = (desde or Path.cwd()).resolve()
    for carpeta in (actual, *actual.parents):
        if (carpeta / FICHERO).exists():
            return carpeta / FICHERO
    raise FileNotFoundError(f"No encuentro {FICHERO} en {actual} ni en sus carpetas padre")


def cargar(ruta: Path | None = None) -> Config:
    """Lee `models.toml` y carga el `.env` de la raíz del repo, si existe.

    Las variables que ya estén definidas en el entorno no se sobrescriben.
    """
    ruta = ruta or buscar_fichero()
    load_dotenv(ruta.resolve().parent.parent / ".env", override=False)
    with ruta.open("rb") as f:
        return Config.model_validate(tomllib.load(f))

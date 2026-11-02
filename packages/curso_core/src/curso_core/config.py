"""Configuración de modelos, proveedores y precios, leída de `config/models.toml`."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

FICHERO = Path("config") / "models.toml"


def alias() -> dict[str, str]:
    """Los roles redirigidos con CURSO_ROLES ("agente=chat_claude,chat=chat_openai")."""
    pares = [p.split("=", 1) for p in os.environ.get("CURSO_ROLES", "").split(",") if "=" in p]
    return {origen.strip(): destino.strip() for origen, destino in pares}


class Proveedor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Dialecto de la API: el nativo de Ollama, el compatible con OpenAI (que hablan
    # OpenAI, Hugging Face, vLLM, llama.cpp y muchos otros), el de Claude, con su SDK, o
    # el de la inferencia de Hugging Face para embeddings (`feature-extraction`), que no
    # tiene versión compatible con OpenAI.
    tipo: Literal["ollama", "openai", "anthropic", "hf_inference"]
    base_url: str
    api_key_env: str | None = None
    # Nombre del límite de tokens de salida en la API compatible con OpenAI. OpenAI ha
    # pasado a `max_completion_tokens`; Ollama, llama.cpp o vLLM siguen con `max_tokens`.
    parametro_max_tokens: str = "max_tokens"
    # Parámetros de la petición que el proveedor rechaza y no se envían (por ejemplo,
    # `temperature` en modelos que solo aceptan el valor por defecto).
    omitir: list[str] = []
    # Si el proveedor exige el JSON Schema "estricto": cada objeto con
    # additionalProperties=false y todas sus propiedades en `required` (OpenAI, Claude).
    esquema_estricto: bool = False
    # Parámetros que se añaden a la petición con `razonar=False`, en proveedores cuyos
    # modelos razonan por defecto (en OpenAI, `reasoning_effort = "none"`).
    sin_razonar: dict[str, str] = {}
    # Valor de `razonar` cuando la práctica no lo fija. Los modelos locales del curso no
    # razonan; un modelo de API que razona por defecto gasta en ello el `max_tokens` de
    # la práctica y devuelve la respuesta vacía. Con `false`, se comporta como el local.
    razonar_por_defecto: bool | None = None
    # Si el proveedor devuelve la probabilidad de cada token (logprobs).
    admite_logprobs: bool = True


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
    # Para CURSO_PROVEEDOR: por cada proveedor alternativo, qué rol sustituye a cada rol
    # local. Los roles que no aparecen se quedan como están.
    alternativas: dict[str, dict[str, str]] = {}

    def resolver(self, rol: str) -> tuple[str, Proveedor, str]:
        """Devuelve (nombre del proveedor, proveedor, modelo) para un rol.

        Dos variables de entorno cambian el modelo sin tocar el código:
        - CURSO_PROVEEDOR (`openai`, `hf`, `claude`...) pasa todos los roles de una
          práctica al proveedor indicado, según la tabla [alternativas] de models.toml.
        - CURSO_ROLES redirige roles concretos: con `CURSO_ROLES=agente=chat_claude`, quien
          pide el rol `agente` recibe el de `chat_claude`. Varias, separadas por comas.
          Tiene prioridad sobre CURSO_PROVEEDOR.
        """
        if rol in (redirigidos := alias()):
            rol = redirigidos[rol]
        elif proveedor := os.environ.get("CURSO_PROVEEDOR"):
            if proveedor not in self.alternativas:
                raise KeyError(
                    f"CURSO_PROVEEDOR={proveedor}: no está en [alternativas] de models.toml"
                    f" (hay: {', '.join(self.alternativas) or 'ninguno'})"
                )
            rol = self.alternativas[proveedor].get(rol, rol)
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


def carpeta_resultados(carpeta: Path) -> Path:
    """Dónde guarda una práctica sus resultados. Con CURSO_PROVEEDOR, en una subcarpeta con
    su nombre (`resultados/openai/`), para no pisar los grabados con el modelo local, que
    son los de las lecciones y los de la regresión del módulo 4."""
    if proveedor := os.environ.get("CURSO_PROVEEDOR"):
        return carpeta / proveedor
    return carpeta


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
        config = Config.model_validate(tomllib.load(f))
    # CURSO_URL_<PROVEEDOR> cambia la URL de un proveedor sin tocar el toml: por ejemplo,
    # dentro de un contenedor, Ollama no está en 127.0.0.1 sino en el anfitrión (lección 6.06).
    for nombre, proveedor in config.providers.items():
        if url := os.environ.get(f"CURSO_URL_{nombre.upper()}"):
            proveedor.base_url = url
    return config

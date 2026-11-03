"""Solución del reto del módulo 0. Los tres cambios están marcados con «Arreglo».

`comprobar_entorno.py` (lección 04) revisa Python, `.env` y los roles, sin llamar a nada.
Este script añade lo que falta para poder trabajar: que Ollama responde, que los modelos de
los roles que sirve Ollama están descargados y que `.env` no está en git.

Comprobar: `uv run python modulos/00-introduccion/reto/comprobar.py --solucion`
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[4]


def ollama_responde(cliente: httpx.Client) -> bool:
    """Si el servidor de Ollama contesta."""
    # Arreglo 1: con Ollama parado, httpx no devuelve un código, lanza ConnectError. Un
    # diagnóstico tiene que decir "no responde", no romperse.
    try:
        return cliente.get("/api/tags").status_code == 200
    except httpx.HTTPError:
        return False


def modelos_descargados(cliente: httpx.Client) -> list[str]:
    """Los nombres que lista Ollama, como `qwen2.5:1.5b`."""
    return [m["name"] for m in cliente.get("/api/tags").json()["models"]]


def modelo_descargado(modelo: str, descargados: list[str]) -> bool:
    """Si el modelo de `models.toml` está entre los descargados."""
    # Arreglo 2: sin etiqueta, Ollama usa `latest`. `bge-m3` en models.toml es
    # `bge-m3:latest` en la lista, y es el mismo modelo.
    return (modelo if ":" in modelo else f"{modelo}:latest") in descargados


def ficheros_en_git(raiz: Path, ruta: str) -> list[str]:
    """Los ficheros que git sigue en esa ruta (vacío si no sigue ninguno)."""
    r = subprocess.run(["git", "ls-files", ruta], cwd=raiz, capture_output=True, text=True)
    return r.stdout.split()


def env_versionado(raiz: Path, listar: Callable[[Path, str], list[str]] = ficheros_en_git) -> bool:
    """Si `.env` está en git (y por tanto, sus claves en el historial)."""
    # Arreglo 3: .gitignore solo impide añadir ficheros nuevos. Si .env se añadió antes de
    # ignorarlo, git lo sigue igual. Hay que preguntar a git qué sigue, no leer .gitignore.
    return ".env" in listar(raiz, ".env")


def main() -> int:
    with (RAIZ / "config" / "models.toml").open("rb") as f:
        config = tomllib.load(f)
    # Los roles servidos por Ollama: los modelos que tienen que estar descargados.
    roles = {
        rol: datos["model"]
        for rol, datos in config["roles"].items()
        if config["providers"].get(datos.get("provider", ""), {}).get("tipo") == "ollama"
    }
    url = config["providers"]["ollama"]["base_url"]
    with httpx.Client(base_url=url, timeout=5) as cliente:
        responde = ollama_responde(cliente)
        print(f"{'OK   ' if responde else 'FALLA'} Ollama responde en {url}")
        if responde:
            descargados = modelos_descargados(cliente)
            for rol, modelo in roles.items():
                ok = modelo_descargado(modelo, descargados)
                print(f"{'OK   ' if ok else 'FALLA'} rol {rol}: {modelo}")
    versionado = env_versionado(RAIZ)
    print(f"{'FALLA' if versionado else 'OK   '} .env fuera de git")
    return 0


if __name__ == "__main__":
    sys.exit(main())

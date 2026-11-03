"""Reto del módulo 0: el diagnóstico del entorno que no deja pasar nada.

`comprobar_entorno.py` (lección 04) revisa Python, `.env` y los roles, sin llamar a nada.
Este script añade lo que falta para poder trabajar: que Ollama responde, que los modelos de
los roles que sirve Ollama están descargados y que `.env` no está en git.

Tiene fallos. `comprobar.py` dice cuáles de sus criterios no cumple; arréglalo hasta que
los cumpla todos.

Uso: `uv run python modulos/00-introduccion/reto/diagnostico.py`
Comprobar: `uv run python modulos/00-introduccion/reto/comprobar.py`
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[3]


def ollama_responde(cliente: httpx.Client) -> bool:
    """Si el servidor de Ollama contesta."""
    return cliente.get("/api/tags").status_code == 200


def modelos_descargados(cliente: httpx.Client) -> list[str]:
    """Los nombres que lista Ollama, como `qwen2.5:1.5b`."""
    return [m["name"] for m in cliente.get("/api/tags").json()["models"]]


def modelo_descargado(modelo: str, descargados: list[str]) -> bool:
    """Si el modelo de `models.toml` está entre los descargados."""
    return modelo in descargados


def ficheros_en_git(raiz: Path, ruta: str) -> list[str]:
    """Los ficheros que git sigue en esa ruta (vacío si no sigue ninguno)."""
    r = subprocess.run(["git", "ls-files", ruta], cwd=raiz, capture_output=True, text=True)
    return r.stdout.split()


def env_versionado(raiz: Path, listar: Callable[[Path, str], list[str]] = ficheros_en_git) -> bool:
    """Si `.env` está en git (y por tanto, sus claves en el historial)."""
    gitignore = raiz / ".gitignore"
    ignorados = gitignore.read_text(encoding="utf-8").split() if gitignore.exists() else []
    return ".env" not in ignorados


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

"""Comprueba los modelos de Ollama para un módulo sin descargarlos automáticamente.

Uso:
  uv run python scripts/preparar_modelos.py --modulo 3
  uv run python scripts/preparar_modelos.py --todos
  uv run python scripts/preparar_modelos.py --rol embeddings --rol judge
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config" / "models.toml"

# Son roles orientativos para empezar las prácticas de cada módulo.
# Algunas lecciones usan además herramientas externas (llama.cpp, vLLM, etc.).
ROLES_POR_MODULO = {
    0: ("chat",),
    1: ("chat", "chat_pequeno", "chat_grande", "razonador"),
    2: ("chat", "chat_grande"),
    3: ("embeddings", "embeddings_otro", "embeddings_ingles"),
    4: ("chat_grande", "judge", "embeddings"),
    5: ("agente", "embeddings", "judge"),
    6: ("chat_grande", "embeddings"),
    7: ("chat", "chat_grande", "embeddings"),
    8: ("chat_grande", "embeddings"),
}


def normalizar(nombre: str) -> str:
    """Ollama suele exponer :latest para modelos sin etiqueta."""
    return nombre if ":" in nombre else f"{nombre}:latest"


def comprobar(roles: list[str], config: dict) -> int:
    modelos = {}
    for rol in roles:
        datos = config["roles"].get(rol)
        if datos is None:
            print(f"ERROR: rol desconocido: {rol}")
            return 2
        proveedor = datos.get("provider", "")
        if config["providers"].get(proveedor, {}).get("tipo") != "ollama":
            print(f"AVISO: {rol} usa {proveedor}; no se descarga con Ollama.")
            continue
        modelos.setdefault(normalizar(datos["model"]), []).append(rol)

    if not modelos:
        print("No hay modelos de Ollama para los roles seleccionados.")
        return 0

    url = config["providers"]["ollama"]["base_url"].rstrip("/") + "/api/tags"
    try:
        with urlopen(url, timeout=5) as respuesta:
            disponibles = json.load(respuesta)
        descargados = {normalizar(m["name"]) for m in disponibles["models"]}
    except (URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: Ollama no responde en {url}: {error}")
        print("Inicia Ollama y vuelve a ejecutar este comando.")
        return 2

    faltan = []
    for nombre, usos in modelos.items():
        estado = "OK   " if nombre in descargados else "FALTA"
        print(f"{estado} {nombre} (roles: {', '.join(usos)})")
        if nombre not in descargados:
            faltan.append(nombre)

    if faltan:
        print("\nDescarga únicamente los modelos que necesites:")
        for nombre in faltan:
            print(f"  ollama pull {nombre}")
        print("\nLos modelos grandes pueden ocupar varios GB de disco y memoria.")
        return 1

    print("\nTodos los modelos seleccionados están descargados.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    opciones = parser.add_mutually_exclusive_group()
    opciones.add_argument("--modulo", type=int, choices=range(9), metavar="0-8")
    opciones.add_argument("--todos", action="store_true")
    opciones.add_argument("--rol", action="append", metavar="NOMBRE")
    args = parser.parse_args()

    with CONFIG.open("rb") as archivo:
        config = tomllib.load(archivo)

    if args.todos:
        roles = list(config["roles"])
    elif args.modulo is not None:
        roles = list(ROLES_POR_MODULO[args.modulo])
    elif args.rol:
        roles = args.rol
    else:
        roles = list(ROLES_POR_MODULO[0])
    print("Comprobación de modelos de Ollama (sin descargas)\n")
    return comprobar(roles, config)


if __name__ == "__main__":
    raise SystemExit(main())

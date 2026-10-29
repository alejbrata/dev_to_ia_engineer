"""Comprueba que el entorno de trabajo del curso está listo.

Revisa la versión de Python, el entorno virtual, las variables de `.env` y los roles
de `config/models.toml`. No llama a ningún proveedor ni imprime el valor de las claves.

Uso: `uv run python modulos/00-introduccion/comprobar_entorno.py`
"""

from __future__ import annotations

import os
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
PYTHON_MINIMO = (3, 12)


def variables_esperadas(ejemplo: Path) -> list[str]:
    """Nombres de las variables declaradas en `.env.example`."""
    return list(dotenv_values(ejemplo))


def estado_variables(nombres: list[str], entorno: Mapping[str, str]) -> dict[str, bool]:
    """Para cada variable, si tiene un valor no vacío."""
    return {nombre: bool(entorno.get(nombre, "").strip()) for nombre in nombres}


def leer_modelos(ruta: Path) -> dict:
    with ruta.open("rb") as f:
        return tomllib.load(f)


def roles_configurados(modelos: dict) -> dict[str, bool]:
    """Para cada rol de `models.toml`, si tiene proveedor y modelo."""
    return {
        rol: bool(datos.get("provider")) and bool(datos.get("model"))
        for rol, datos in modelos.get("roles", {}).items()
    }


def marca(ok: bool) -> str:
    return "OK " if ok else "-- "


def main() -> int:
    errores = 0

    version = sys.version_info[:2]
    python_ok = version >= PYTHON_MINIMO
    errores += not python_ok
    en_venv = sys.prefix != sys.base_prefix
    print("Python")
    print(f"  {marca(python_ok)}versión {version[0]}.{version[1]} (mínimo 3.12)")
    print(f"  {marca(en_venv)}entorno virtual: {sys.executable}")

    env = RAIZ / ".env"
    print("\nVariables (.env)")
    if env.exists():
        load_dotenv(env)
        print(f"  {marca(True)}encontrado {env}")
    else:
        errores += 1
        print(f"  {marca(False)}no existe {env}: copia .env.example a .env")
    for nombre, ok in estado_variables(
        variables_esperadas(RAIZ / ".env.example"), os.environ
    ).items():
        print(f"  {marca(ok)}{nombre}")

    print("\nModelos (config/models.toml)")
    for rol, ok in roles_configurados(leer_modelos(RAIZ / "config" / "models.toml")).items():
        print(f"  {marca(ok)}{rol}")

    print("\nTodo listo." if errores == 0 else f"\n{errores} problema(s) que corregir.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())

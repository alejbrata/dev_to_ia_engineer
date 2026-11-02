"""Tests de tu proyecto que no necesitan modelos. Añade los de tu lógica."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))


def cargar(nombre: str):
    """Carga un módulo de esta carpeta por su ruta. Con `import evaluar`, pytest podría
    darte el evaluar.py de otra carpeta del repositorio (el del módulo 4 se llama igual)."""
    spec = importlib.util.spec_from_file_location(f"proyecto_{nombre}", AQUI / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_puntuar_ignora_mayusculas() -> None:
    evaluar = cargar("evaluar")
    assert evaluar.puntuar("200", "El límite es de 200 conexiones.")
    assert not evaluar.puntuar("250", "El límite es de 200 conexiones.")

"""Tests de la rúbrica: el nivel que permite la evidencia."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rubrica  # noqa: E402


def test_el_ejemplo_es_coherente_con_su_evidencia() -> None:
    filas = rubrica.contrastar(Path(rubrica.AQUI) / "ejemplo" / "proyecto.toml")
    assert [f["criterio"] for f in filas if f["problemas"]] == []
    evaluacion = next(f for f in filas if f["criterio"] == "Evaluación")
    # 52 de 58 con un intervalo que baja del 80 %: el aviso limita el nivel.
    assert evaluacion["tope"] == "suficiente"

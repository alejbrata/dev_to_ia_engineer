"""Tests del módulo 7 que no necesitan modelos ni red."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import decidir  # noqa: E402
import preparar  # noqa: E402


@pytest.mark.parametrize(
    ("otro", "esperado"),
    [
        ("Qwen2.5-7B-Instruct", True),
        ("Qwen2.5-0.5B-Instruct", True),
        ("Qwen2.5-1.5B-Instruct-GGUF", False),
        ("Qwen2.5-Coder-1.5B-Instruct", False),
        ("Qwen2.5-1.5B", False),
    ],
)
def test_misma_familia(otro: str, esperado: bool) -> None:
    assert preparar.misma_familia("Qwen2.5-1.5B-Instruct", otro) is esperado


def test_resumen_de_un_modelo_que_siempre_se_abstiene() -> None:
    import dataset

    casos = dataset.cargar()
    r = decidir.resumen({c.id: "No aparece en la documentación." for c in casos}, casos)
    total, con, sin = r["n"]
    assert r["no_deben_responderse"] == sin
    assert r["con_respuesta"] == 0
    # Abstenerse cuando había respuesta es un fallo, pero no es inventar.
    assert r["inventa"] == 0
    assert r["total"] == sin == total - con

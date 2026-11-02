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


def test_tipos_de_tensor_lee_el_registro_de_llama_quantize() -> None:
    import cuantizar

    registro = (
        "[   1/ 339] output.weight - [  1536, 151936,      1,      1], type =    f16, "
        "converting to q6_K .. size =   445.12 MiB ->   182.57 MiB\n"
        "[   4/ 339] blk.0.attn_k.bias - [   256,      1,      1,      1], type =    f32, "
        "size =    0.001 MiB\n"
        "[   9/ 339] blk.0.attn_q.weight - [  1536,   1536,      1,      1], type =    f16, "
        "converting to q4_K .. size =     4.50 MiB ->     1.27 MiB\n"
    )
    assert cuantizar.tipos_de_tensor(registro) == {"output": "q6_K", "blk.0.attn_q": "q4_K"}


def test_p95() -> None:
    import servir

    assert servir.p95([1.0, 2.0, 3.0]) == 3.0
    assert servir.p95([float(i) for i in range(1, 101)]) == 95.0

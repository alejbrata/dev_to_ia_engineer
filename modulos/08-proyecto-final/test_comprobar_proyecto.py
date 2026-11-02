"""Tests del comprobador del proyecto final, con proyectos de mentira en carpetas temporales."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comprobar_proyecto as cp  # noqa: E402


def test_especificacion_incompleta() -> None:
    c = cp.comprobar_especificacion({"especificacion": {"problema": "algo", "umbral": 0.8}})
    assert c.estado == "FALTA"
    assert "usuarios" in c.evidencia and "problema" not in c.evidencia


def test_dataset_con_pocos_casos(tmp_path: Path) -> None:
    datos = tmp_path / "casos.jsonl"
    datos.write_text("\n".join(json.dumps({"id": i}) for i in range(10)), encoding="utf-8")
    c = cp.comprobar_dataset(tmp_path, {"evals": {"dataset": "casos.jsonl"}})
    assert c.estado == "FALTA"
    assert c.evidencia.startswith("10 casos")


def test_resultados_por_debajo_del_umbral_es_aviso(tmp_path: Path) -> None:
    filas = [{"version": "x"}] + [{"caso": str(i), "ok": i < 52} for i in range(58)]
    (tmp_path / "r.jsonl").write_text("\n".join(map(json.dumps, filas)), encoding="utf-8")
    m = {"evals": {"resultados": "r.jsonl"}, "especificacion": {"umbral": 0.8}}
    c = cp.comprobar_resultados(tmp_path, m)
    assert c.estado == "AVISO"
    assert c.evidencia.startswith("52 de 58")


def test_coste_necesita_tokens_latencia_y_dinero(tmp_path: Path) -> None:
    (tmp_path / "m.json").write_text('{"tokens_entrada": 1, "latencia_p50_s": 2}', "utf-8")
    c = cp.comprobar_coste(tmp_path, {"coste": {"medidas": ["m.json"]}})
    assert c.estado == "FALTA" and "dinero" in c.evidencia


def test_readme_con_secciones(tmp_path: Path) -> None:
    secciones = "\n".join(f"## {s.capitalize()}" for s in cp.SECCIONES_README)
    (tmp_path / "README.md").write_text(f"# P\n{secciones}\n", encoding="utf-8")
    assert cp.comprobar_readme(tmp_path, {}).estado == "OK"
    (tmp_path / "README.md").write_text("# P\n## Problema\n", encoding="utf-8")
    assert cp.comprobar_readme(tmp_path, {}).estado == "FALTA"

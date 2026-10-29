"""Comprueba que la web y las carpetas del repo reflejan docs/PLAN.md."""

import json

import plan_sync

ROOT = plan_sync.ROOT

GRUPOS = plan_sync.parse_plan()
MODULOS = [g for g in GRUPOS if g.directory != plan_sync.ANEXOS_DIR]


def test_plan_tiene_modulos_y_anexos() -> None:
    assert [g.directory[:2] for g in MODULOS] == [f"{n:02d}" for n in range(9)]
    assert GRUPOS[-1].directory == plan_sync.ANEXOS_DIR
    assert all(g.paginas for g in GRUPOS)


def test_sidebar_generado_desde_el_plan() -> None:
    sidebar = json.loads(plan_sync.SIDEBAR.read_text(encoding="utf-8"))
    assert sidebar == plan_sync.sidebar(GRUPOS)


def test_paginas_coinciden_con_el_plan() -> None:
    esperadas = {f"{g.directory}/{p.slug}.md" for g in GRUPOS for p in g.paginas}
    existentes = {
        p.relative_to(plan_sync.DOCS).as_posix()
        for p in plan_sync.DOCS.rglob("*.md*")
        if p.name not in {"index.mdx", "404.md"}
    }
    assert existentes == esperadas


def test_carpetas_de_modulos() -> None:
    existentes = {
        p.name
        for p in (ROOT / "modulos").iterdir()
        if p.is_dir() and not p.name.startswith((".", "_"))
    }
    assert existentes == {g.directory for g in MODULOS}


def test_bitacoras_por_modulo() -> None:
    existentes = {p.stem for p in (ROOT / "bitacora").glob("*.md")}
    assert existentes == {g.directory for g in MODULOS}

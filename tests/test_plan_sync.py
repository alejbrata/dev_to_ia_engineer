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
    # Las lecciones pueden ser .md o .mdx (las que usan componentes interactivos).
    esperadas = {f"{g.directory}/{p.slug}" for g in GRUPOS for p in g.paginas}
    existentes = {
        p.relative_to(plan_sync.DOCS).with_suffix("").as_posix()
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
    # El código de un anexo con prácticas vive en una carpeta con su nombre (b-hugging-face).
    anexos = {p.slug for g in GRUPOS if g.directory == plan_sync.ANEXOS_DIR for p in g.paginas}
    assert existentes - anexos == {g.directory for g in MODULOS}


def test_la_bitacora_es_un_solo_fichero() -> None:
    """El contenido personal va entero al anexo H, desde un único fichero (2026-11-03)."""
    assert {p.name for p in (ROOT / "bitacora").glob("*.md")} == {"proceso.md"}

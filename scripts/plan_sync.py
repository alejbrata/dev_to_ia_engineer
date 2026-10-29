"""Sincroniza la web con el temario de docs/PLAN.md.

Lee los módulos, lecciones y anexos del plan y:

- escribe el sidebar de Starlight en site/src/sidebar.json;
- crea el esqueleto de las páginas que falten en site/src/content/docs/.

Nunca sobrescribe una página existente. Uso: `uv run python scripts/plan_sync.py`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "docs" / "PLAN.md"
DOCS = ROOT / "site" / "src" / "content" / "docs"
SIDEBAR = ROOT / "site" / "src" / "sidebar.json"

ANEXOS_DIR = "anexos"
ANEXOS_LABEL = "Anexos"

SECCIONES = [
    "Objetivos",
    "Teoría",
    "Práctica",
    "Mide y depura",
    "Errores frecuentes",
    "Bitácora",
    "Para profundizar",
]

MODULO_RE = re.compile(r"^## Módulo (\d+) — (.+?)\s*[⬜🟨✅]?\s*$")
ANEXOS_RE = re.compile(r"^## Anexos\b")
LECCION_RE = re.compile(r"^(\d+)\. (.+)$")
ANEXO_RE = re.compile(r"^- \*\*([A-Z])\. (.+?)\*\*(?::\s*(.+))?$")


@dataclass
class Pagina:
    slug: str
    title: str
    description: str


@dataclass
class Grupo:
    label: str
    directory: str
    paginas: list[Pagina] = field(default_factory=list)


def slugify(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


def limpiar(texto: str) -> str:
    """Quita el marcado Markdown y las notas en cursiva del plan."""
    texto = re.sub(r"\s*\*\(.*?\)\*", "", texto)
    texto = texto.replace("**", "").replace("`", "")
    return texto.strip()


def leccion(numero: int, linea: str) -> Pagina:
    description = limpiar(linea)
    title = description.split(":", 1)[0].strip()
    return Pagina(f"{numero:02d}-{slugify(title)}", title, description)


def parse_plan(texto: str | None = None) -> list[Grupo]:
    texto = PLAN.read_text(encoding="utf-8") if texto is None else texto
    grupos: list[Grupo] = []
    actual: Grupo | None = None
    for linea in texto.splitlines():
        if m := MODULO_RE.match(linea):
            numero, nombre = int(m[1]), m[2]
            actual = Grupo(
                f"Módulo {numero} — {nombre}", f"{numero:02d}-{slugify(nombre)}"
            )
            grupos.append(actual)
        elif ANEXOS_RE.match(linea):
            actual = Grupo(ANEXOS_LABEL, ANEXOS_DIR)
            grupos.append(actual)
        elif actual is None:
            continue
        elif actual.directory != ANEXOS_DIR and (m := LECCION_RE.match(linea)):
            actual.paginas.append(leccion(int(m[1]), m[2]))
        elif actual.directory == ANEXOS_DIR and (m := ANEXO_RE.match(linea)):
            letra, nombre, resto = m[1], m[2], m[3]
            title = f"{letra}. {limpiar(nombre)}"
            description = f"{limpiar(nombre)}: {limpiar(resto)}" if resto else limpiar(nombre)
            actual.paginas.append(Pagina(f"{letra.lower()}-{slugify(nombre)}", title, description))
    return grupos


def sidebar(grupos: list[Grupo]) -> list[dict]:
    return [
        {"label": g.label, "items": [{"autogenerate": {"directory": g.directory}}]}
        for g in grupos
    ]


def frontmatter(pagina: Pagina) -> str:
    return (
        "---\n"
        f"title: {json.dumps(pagina.title, ensure_ascii=False)}\n"
        f"description: {json.dumps(pagina.description, ensure_ascii=False)}\n"
        "---\n"
    )


def cuerpo_leccion() -> str:
    bloques = []
    for seccion in SECCIONES:
        todo = "TODO(alex)" if seccion == "Bitácora" else "TODO"
        bloques.append(f"## {seccion}\n\n{todo}\n")
    return "\n".join(bloques)


def contenido(grupo: Grupo, pagina: Pagina) -> str:
    cuerpo = "TODO\n" if grupo.directory == ANEXOS_DIR else cuerpo_leccion()
    return f"{frontmatter(pagina)}\n{cuerpo}"


def main() -> None:
    grupos = parse_plan()
    SIDEBAR.write_text(
        json.dumps(sidebar(grupos), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    creadas = 0
    for grupo in grupos:
        for pagina in grupo.paginas:
            ruta = DOCS / grupo.directory / f"{pagina.slug}.md"
            if ruta.exists():
                continue
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(contenido(grupo, pagina), encoding="utf-8", newline="\n")
            creadas += 1
    total = sum(len(g.paginas) for g in grupos)
    print(f"{len(grupos)} grupos, {total} páginas, {creadas} creadas.")


if __name__ == "__main__":
    main()

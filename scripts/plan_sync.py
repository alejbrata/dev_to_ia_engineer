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
    "Comprueba lo que has entendido",
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


# Slugs cortos para títulos largos. El resto se deriva del título.
SLUGS = {
    "Prompting y salida estructurada": "prompting",
    "Cómo funciona un LLM sin matemáticas innecesarias": "como-funciona-un-llm",
    "Ventana de contexto, límites y qué pasa cuando te pasas": "ventana-de-contexto",
    "Modelos abiertos frente a cerrados; primer contacto con Hugging Face": "abiertos-y-cerrados",
    "Few-shot y técnicas que sí funcionan (y mitos que no)": "few-shot",
    "Generación con citas y control de alucinaciones": "generacion-con-citas",
    "El bucle de un agente desde cero (sin framework)": "bucle-de-un-agente",
    "Guardrails y validación de entrada y salida": "guardrails",
    "Inferencia local (Ollama, llama.cpp, vLLM)": "inferencia-local",
    "Evaluar el modelo ajustado frente al base": "evaluar-el-modelo-ajustado",
    "Cómo presentarlo como proyecto de portafolio": "portafolio",
    "Herramientas y estrategias de desarrollo con IA": "desarrollo-con-ia",
}


def slugify(texto: str) -> str:
    if texto in SLUGS:
        return SLUGS[texto]
    texto = re.sub(r"\s*\(.*?\)", "", texto)
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
            actual = Grupo(f"Módulo {numero} — {nombre}", f"{numero:02d}-{slugify(nombre)}")
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
        {"label": g.label, "items": [{"autogenerate": {"directory": g.directory}}]} for g in grupos
    ]


def frontmatter(pagina: Pagina) -> str:
    return (
        "---\n"
        f"title: {json.dumps(pagina.title, ensure_ascii=False)}\n"
        f"description: {json.dumps(pagina.description, ensure_ascii=False)}\n"
        "---\n"
    )


PLAN_URL = "https://github.com/alejbrata/dev_to_ia_engineer/blob/main/docs/PLAN.md"


def aviso(frase: str) -> str:
    """Lo que ve quien abre una página que aún no está escrita."""
    return (
        ":::note[En preparación]\n"
        f"{frase} El temario completo y el estado de cada módulo están en "
        f"[docs/PLAN.md]({PLAN_URL}). Cuando se publique, lo tendrás aquí al actualizar tu fork.\n"
        ":::\n"
    )


def cuerpo_leccion() -> str:
    # La estructura queda en un comentario, a mano para quien escriba la lección.
    secciones = "\n".join(f"## {seccion}" for seccion in SECCIONES)
    return f"{aviso('Esta lección aún no está escrita.')}\n<!--\n{secciones}\n-->\n"


def contenido(grupo: Grupo, pagina: Pagina) -> str:
    if grupo.directory == ANEXOS_DIR:
        cuerpo = aviso("Este anexo aún no está escrito.")
    else:
        cuerpo = cuerpo_leccion()
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
            # Una lección puede haberse convertido a MDX para usar componentes.
            if ruta.exists() or ruta.with_suffix(".mdx").exists():
                continue
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(contenido(grupo, pagina), encoding="utf-8", newline="\n")
            creadas += 1
    total = sum(len(g.paginas) for g in grupos)
    print(f"{len(grupos)} grupos, {total} páginas, {creadas} creadas.")


if __name__ == "__main__":
    main()

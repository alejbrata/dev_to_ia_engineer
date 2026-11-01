"""Skills: conocimiento que el agente carga cuando lo necesita (lección 14).

Una skill es una carpeta con un `SKILL.md`: unas líneas de cabecera con su nombre y una
descripción, y después las instrucciones. El agente empieza viendo solo el nombre y la
descripción de cada una (pocos tokens); cuando una tarea encaja, carga la skill entera. Es
lo que el formato abierto Agent Skills llama revelación progresiva (*progressive
disclosure*).

Aquí, cada runbook del corpus y los criterios de severidad se convierten en una skill. La
descripción es el título y la primera frase del documento ("Usa este runbook cuando...").
"""

from __future__ import annotations

import corpus
from curso_core import Herramienta, LlamadaHerramienta
from plataforma import HERRAMIENTAS, Plataforma
from pydantic import BaseModel, Field


class Skill(BaseModel):
    nombre: str
    descripcion: str
    contenido: str

    def como_skill_md(self) -> str:
        """El fichero SKILL.md, en el formato de Agent Skills."""
        return f"---\nname: {self.nombre}\ndescription: {self.descripcion}\n---\n\n{self.contenido}"


def desde_corpus() -> list[Skill]:
    skills = []
    for nombre, texto in corpus.documentos().items():
        if not (nombre.startswith("runbook-") or nombre == "severidades"):
            continue
        lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
        titulo = lineas[0].lstrip("# ")
        skills.append(Skill(nombre=nombre, descripcion=f"{titulo}. {lineas[1]}", contenido=texto))
    return skills


def catalogo(skills: list[Skill]) -> str:
    """Lo que el agente ve siempre: una línea por skill."""
    return "\n".join(f"- {s.nombre}: {s.descripcion}" for s in skills)


def todo(skills: list[Skill]) -> str:
    """La alternativa: todas las skills, enteras, en el prompt."""
    return "\n\n".join(s.contenido for s in skills)


class ArgsSkill(BaseModel):
    nombre: str = Field(description="El nombre de la skill, tal como aparece en el catálogo.")


CARGAR_SKILL = Herramienta.desde(
    "cargar_skill",
    "Carga el contenido completo de una skill del catálogo (un runbook o los criterios de "
    "severidad). Cárgala antes de decidir la severidad o la mitigación.",
    ArgsSkill,
)
SIN_BUSQUEDA = [h for h in HERRAMIENTAS if h.nombre != "buscar_documentacion"]


class PlataformaSkills:
    """Las herramientas de siempre, sin búsqueda en la documentación, y cargar_skill."""

    def __init__(self, p: Plataforma, skills: list[Skill]):
        self.p = p
        self.escenario = p.escenario
        self.skills = {s.nombre: s for s in skills}
        self.cargadas: list[str] = []

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        if llamada.nombre == "cargar_skill":
            nombre = str(llamada.argumentos.get("nombre", ""))
            skill = self.skills.get(nombre)
            if skill is None:
                return f"Error: no hay ninguna skill llamada {nombre!r}.", False
            self.cargadas.append(nombre)
            # Para que comprobar() sepa que consultó el runbook, como con la búsqueda.
            self.p.consultados.append(nombre)
            return skill.contenido, True
        return self.p.ejecutar(llamada)

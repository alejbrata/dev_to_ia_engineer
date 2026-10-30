"""Prompts como código: plantillas en ficheros Markdown versionados.

Cada prompt es un fichero `prompts/<tarea>/<variante>.md` con una cabecera y secciones:

    ---
    version: 2
    descripcion: Clasifica un ticket de incidencias.
    variables: ticket
    ---

    ## Sistema
    Instrucciones generales...

    ## Ejemplos            (opcional: pares de mensajes para few-shot)
    ### Usuario
    ...
    ### Asistente
    ...

    ## Usuario
    Ticket: {{ticket}}

Las variables se escriben `{{nombre}}`. Rellenar una variable que no existe, dejar una sin
rellenar o pasar una que el prompt no declara es un error: mejor fallar aquí que mandar
`{{ticket}}` al modelo.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from curso_core import config as cfg
from curso_core.client import Mensaje, PromptRenderizado

VARIABLE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
SECCION = re.compile(r"^## (Sistema|Ejemplos|Usuario)\s*$", re.M)
TURNO = re.compile(r"^### (Usuario|Asistente)\s*$", re.M)


class ErrorPrompt(Exception):
    """Prompt mal formado o variables que no encajan."""


class Prompt(BaseModel):
    nombre: str
    version: int
    descripcion: str = ""
    variables: list[str] = []
    sistema: str = ""
    ejemplos: list[Mensaje] = []
    usuario: str

    @property
    def id(self) -> str:
        """Identificador para las trazas: `tarea/variante@vN`."""
        return f"{self.nombre}@v{self.version}"


def carpeta_por_defecto() -> Path:
    """`prompts/` en la raíz del repo (junto a `config/`)."""
    return cfg.buscar_fichero().resolve().parent.parent / "prompts"


def _cabecera(texto: str) -> tuple[dict[str, str], str]:
    if not texto.startswith("---\n"):
        raise ErrorPrompt("Falta la cabecera (bloque entre líneas ---)")
    fin = texto.index("\n---\n", 4)
    campos = {}
    for linea in texto[4:fin].splitlines():
        if linea.strip():
            clave, _, valor = linea.partition(":")
            campos[clave.strip()] = valor.strip()
    return campos, texto[fin + 5 :]


def _secciones(cuerpo: str) -> dict[str, str]:
    partes = SECCION.split(cuerpo)
    # partes = [antes, nombre1, contenido1, nombre2, contenido2, ...]
    return {partes[i]: partes[i + 1].strip() for i in range(1, len(partes), 2)}


def _ejemplos(texto: str) -> list[Mensaje]:
    partes = TURNO.split(texto)
    roles = {"Usuario": "user", "Asistente": "assistant"}
    return [
        Mensaje(role=roles[partes[i]], content=partes[i + 1].strip())
        for i in range(1, len(partes), 2)
    ]


def leer(ruta: Path, nombre: str) -> Prompt:
    campos, cuerpo = _cabecera(ruta.read_text(encoding="utf-8"))
    secciones = _secciones(cuerpo)
    if "Usuario" not in secciones:
        raise ErrorPrompt(f"{ruta.name}: falta la sección '## Usuario'")
    return Prompt(
        nombre=nombre,
        version=int(campos.get("version", 1)),
        descripcion=campos.get("descripcion", ""),
        variables=[v.strip() for v in campos.get("variables", "").split(",") if v.strip()],
        sistema=secciones.get("Sistema", ""),
        ejemplos=_ejemplos(secciones.get("Ejemplos", "")),
        usuario=secciones["Usuario"],
    )


def cargar(nombre: str, carpeta: Path | None = None) -> Prompt:
    """Carga `prompts/<nombre>.md`, por ejemplo `cargar("tickets/completo")`."""
    ruta = (carpeta or carpeta_por_defecto()) / f"{nombre}.md"
    if not ruta.exists():
        raise ErrorPrompt(f"No existe el prompt {ruta}")
    return leer(ruta, nombre)


def _rellenar(texto: str, valores: dict[str, str]) -> str:
    return VARIABLE.sub(lambda m: valores[m[1]], texto)


def renderizar(prompt: Prompt, **valores: str) -> PromptRenderizado:
    faltan = set(prompt.variables) - set(valores)
    sobran = set(valores) - set(prompt.variables)
    if faltan or sobran:
        raise ErrorPrompt(
            f"{prompt.id}: faltan variables {sorted(faltan)}, sobran {sorted(sobran)}"
        )
    textos = [prompt.sistema, prompt.usuario, *(m.content for m in prompt.ejemplos)]
    usadas = {v for t in textos for v in VARIABLE.findall(t)}
    if no_declaradas := usadas - set(prompt.variables):
        raise ErrorPrompt(f"{prompt.id}: usa variables no declaradas {sorted(no_declaradas)}")

    mensajes = []
    if prompt.sistema:
        mensajes.append(Mensaje(role="system", content=_rellenar(prompt.sistema, valores)))
    mensajes += [
        Mensaje(role=m.role, content=_rellenar(m.content, valores)) for m in prompt.ejemplos
    ]
    mensajes.append(Mensaje(role="user", content=_rellenar(prompt.usuario, valores)))
    return PromptRenderizado(id=prompt.id, mensajes=mensajes)

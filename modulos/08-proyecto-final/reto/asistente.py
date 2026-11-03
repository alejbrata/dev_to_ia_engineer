"""Reto del módulo 8: un problema que no conoces.

Arce Distribución (una empresa inventada) quiere un asistente que responda a las preguntas de
su plantilla sobre las políticas internas: vacaciones, teletrabajo, viajes, equipos, formación,
horario, permisos y seguridad. Las políticas están en `docs/`, ocho documentos en Markdown que
no has visto en el curso. Si algo no está en ellas, el asistente tiene que decir "No aparece en
la documentación".

Este asistente es la línea base: el modelo responde sin los documentos. Constrúyelo como
quieras, con lo que has aprendido en el curso. `comprobar.py` lo mide con las 20 preguntas de
desarrollo; cuando estés conforme, y solo entonces, con las 20 de prueba (`--prueba`).

No cambies los documentos ni las preguntas. La única regla del sistema: `responder` recibe un
cliente y una pregunta y devuelve el texto de la respuesta.

Comprobar: `uv run python modulos/08-proyecto-final/reto/comprobar.py [--prueba]`
"""

from __future__ import annotations

from pathlib import Path

from curso_core import ClienteLLM, Mensaje, Opciones

# Los documentos, también desde solucion/: están en la carpeta del reto.
DOCS = next(p for p in Path(__file__).resolve().parents if p.name == "reto") / "docs"
ROL = "chat"
ABSTENCION = "No aparece en la documentación"
OPCIONES = Opciones(temperatura=0, max_tokens=300)


def documentos() -> dict[str, str]:
    return {f.stem: f.read_text(encoding="utf-8") for f in sorted(DOCS.glob("*.md"))}


def responder(cliente: ClienteLLM, pregunta: str) -> str:
    mensajes = [
        Mensaje(
            role="system",
            content="Eres el asistente de Personas de Arce Distribución. Responde en español, "
            f'en una o dos frases. Si no lo sabes, responde "{ABSTENCION}".',
        ),
        Mensaje(role="user", content=pregunta),
    ]
    return cliente.chat(mensajes, rol=ROL, opciones=OPCIONES).texto.strip()

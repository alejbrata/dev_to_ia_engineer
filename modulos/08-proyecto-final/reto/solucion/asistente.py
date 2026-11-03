"""Solución de referencia del reto del módulo 8: el RAG del curso, sin piezas nuevas.

- Troceado por secciones de Markdown, con el título del documento y de la sección (3.02).
- Búsqueda densa con el modelo de embeddings del rol `embeddings`, 3 fragmentos (3.03).
- Un prompt que responde solo con los fragmentos, da todos los pasos y se abstiene si el dato
  no está (3.06 y 4.06).
- El modelo de 7B (`chat_grande`). En desarrollo, el de 1,5B ya llega (17 de 20), pero falla una
  de las que no tienen respuesta; el de 7B, 19 de 20 y las 4.

No es la única forma: es una que llega a los criterios. Mídela contra la tuya.
Comprobar: `uv run python modulos/08-proyecto-final/reto/comprobar.py --solucion [--prueba]`
"""

from __future__ import annotations

from pathlib import Path

from curso_core import ClienteLLM, Mensaje, Opciones
from curso_core.rag import IndiceVectorial, trocear_por_secciones

DOCS = next(p for p in Path(__file__).resolve().parents if p.name == "reto") / "docs"
ROL = "chat_grande"
K = 3
ABSTENCION = "No aparece en la documentación"
OPCIONES = Opciones(temperatura=0, max_tokens=300)
SISTEMA = f"""Eres el asistente de Personas de Arce Distribución. Respondes en español, en una a \
tres frases, a preguntas de la plantilla sobre las políticas internas.

Reglas:
- Usa solo los fragmentos de las políticas que se te dan. No uses lo que sepas de otras empresas.
- Si la respuesta tiene varios pasos o condiciones, da todos.
- Si los fragmentos no dicen lo que se pregunta, responde exactamente: "{ABSTENCION}". No \
respondas con un dato parecido de otra política."""

_indices: dict[int, IndiceVectorial] = {}


def documentos() -> dict[str, str]:
    return {f.stem: f.read_text(encoding="utf-8") for f in sorted(DOCS.glob("*.md"))}


def indice(cliente: ClienteLLM) -> IndiceVectorial:
    """El índice se construye una vez por cliente: son 8 documentos, unos segundos."""
    if id(cliente) not in _indices:
        nuevo = IndiceVectorial(cliente, rol="embeddings")
        nuevo.añadir([f for d, t in documentos().items() for f in trocear_por_secciones(d, t)])
        _indices[id(cliente)] = nuevo
    return _indices[id(cliente)]


def responder(cliente: ClienteLLM, pregunta: str) -> str:
    fragmentos = indice(cliente).buscar(pregunta, K)
    contexto = "\n\n".join(
        f"[{i}] {r.fragmento.titulo}\n{r.fragmento.texto}" for i, r in enumerate(fragmentos, 1)
    )
    mensajes = [
        Mensaje(role="system", content=SISTEMA),
        Mensaje(role="user", content=f"Fragmentos:\n\n{contexto}\n\nPregunta: {pregunta}"),
    ]
    return cliente.chat(mensajes, rol=ROL, opciones=OPCIONES).texto.strip()

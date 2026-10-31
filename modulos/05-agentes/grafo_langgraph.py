"""El grafo del agente de guardia con LangGraph (lección 06).

Los nodos y la condición son los de `grafo_guardia.py`, sin cambiar una línea. Cambia el
motor:

- El estado y las aristas se declaran con `StateGraph`.
- Los checkpoints los guarda un `checkpointer` (aquí SQLite, en un fichero).
- La aprobación humana es un nodo más, `aprobar`, que llama a `interrupt()`: el grafo se
  para ahí y se reanuda con `Command(resume=...)`, cuyo valor devuelve `interrupt()`.
"""

from __future__ import annotations

from grafo import FIN
from grafo_guardia import EstadoGuardia, NodosGuardia, tras_decidir
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from workflow import Decision


def aprobar(e: EstadoGuardia) -> dict:
    """Para el grafo y espera la decisión de una persona sobre la propuesta."""
    respuesta = interrupt({"servicio": e.servicio, "decision": e.decision.model_dump()})
    cambios = {"aprobada": respuesta["aprobada"]}
    if "decision" in respuesta:  # la persona ha corregido la propuesta
        cambios["decision"] = Decision.model_validate(respuesta["decision"])
    return cambios


def construir(nodos: NodosGuardia, checkpointer):
    g = StateGraph(EstadoGuardia)
    g.add_node("clasificar", nodos.clasificar)
    g.add_node("recoger", nodos.recoger)
    g.add_node("decidir", nodos.decidir)
    g.add_node("aprobar", aprobar)
    g.add_node("abrir", nodos.abrir)
    g.add_edge(START, "clasificar")
    g.add_edge("clasificar", "recoger")
    g.add_edge("recoger", "decidir")
    # La misma condición que con el motor propio; el mapa traduce sus nombres a los de aquí.
    g.add_conditional_edges(
        "decidir", tras_decidir, {"decidir": "decidir", "abrir": "aprobar", FIN: END}
    )
    g.add_edge("aprobar", "abrir")
    g.add_edge("abrir", END)
    return g.compile(checkpointer=checkpointer)

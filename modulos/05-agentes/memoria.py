"""Contexto y memoria del agente (lección 07).

- Contexto: lo que el modelo ve en cada paso. En el bucle de la lección 03 crece con cada
  resultado de herramienta. `recortar` deja enteros solo los últimos resultados y abrevia
  los antiguos.
- Memoria a largo plazo: lo que sobrevive entre ejecuciones. Aquí, las notas que deja la
  persona de guardia al cerrar cada escenario (qué severidad era y por qué, qué mitigación).
  Antes de empezar, el agente recibe las notas de las alertas más parecidas.
"""

from __future__ import annotations

from collections.abc import Callable

from curso_core import ClienteLLM, Mensaje
from curso_core.rag import Fragmento, IndiceVectorial
from plataforma import Escenario

CONSERVAR = 2
ABREVIAR_A = 200


def recortar(
    conservar: int = CONSERVAR, abreviar_a: int = ABREVIAR_A
) -> Callable[[list[Mensaje]], list[Mensaje]]:
    """Deja enteros los `conservar` últimos resultados de herramienta; de los anteriores,
    solo los primeros `abreviar_a` caracteres."""

    def aplicar(mensajes: list[Mensaje]) -> list[Mensaje]:
        resultados = [i for i, m in enumerate(mensajes) if m.role == "tool"]
        antiguos = set(resultados[:-conservar]) if conservar else set(resultados)
        return [
            m.model_copy(update={"content": abreviar(m.content, abreviar_a)})
            if i in antiguos
            else m
            for i, m in enumerate(mensajes)
        ]

    return aplicar


def abreviar(texto: str, limite: int) -> str:
    if len(texto) <= limite:
        return texto
    return f"{texto[:limite]}… [recortado: {len(texto) - limite} caracteres más]"


class Memoria:
    """Las notas de escenarios ya cerrados, buscables por parecido con la alerta."""

    def __init__(self, cliente: ClienteLLM, escenarios: list[Escenario]):
        self.indice = IndiceVectorial(cliente)
        self.indice.añadir(
            [
                Fragmento(id=e.id, doc=e.id, titulo=e.alerta, texto=e.esperado.nota)
                for e in escenarios
            ]
        )

    def buscar(self, alerta: str, *, k: int = 2, excluir: str | None = None) -> list[Fragmento]:
        """Las `k` notas más parecidas. `excluir` deja fuera el propio escenario: al medir,
        el agente no puede recordar la solución del caso que está resolviendo."""
        resultados = self.indice.buscar(alerta, k + 1)
        return [r.fragmento for r in resultados if r.fragmento.doc != excluir][:k]


def como_texto(notas: list[Fragmento]) -> str:
    return "\n".join(f"- Alerta: {n.titulo}\n  Nota al cerrarla: {n.texto}" for n in notas)

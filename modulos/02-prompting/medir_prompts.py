"""Medir variantes de un prompt con los mismos tickets. Lo usan varias prácticas del módulo.

Para cada variante cuenta las respuestas utilizables (con el formato pedido y valores
válidos), los aciertos por campo frente a la clasificación esperada, los tokens y la
latencia, y guarda el detalle ticket a ticket.

Antes de cada variante descarga el modelo de Ollama, para que todas partan del mismo
estado: con la caché del prompt de la variante anterior, los resultados cambian incluso
con temperatura 0 (lección 02 del módulo 2).
"""

from __future__ import annotations

import httpx
import tickets
from curso_core import ClienteLLM, Opciones, prompts
from pydantic import BaseModel

OPCIONES = Opciones(temperatura=0, max_tokens=200)


class Medida(BaseModel):
    variante: str
    utilizables: int = 0
    aciertos: dict[str, int] = {c: 0 for c in tickets.CAMPOS}
    todo_bien: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    latencia: float = 0.0
    ejemplo: str = ""
    predicciones: list[tickets.Clasificacion | None] = []
    detalle: list[str] = []


def empezar_de_cero(cliente: ClienteLLM, rol: str = "chat") -> None:
    """Descarga el modelo de Ollama (keep_alive=0): la siguiente llamada lo carga limpio."""
    _, proveedor, modelo = cliente.config.resolver(rol)
    if proveedor.tipo == "ollama":
        httpx.post(
            f"{proveedor.base_url}/api/generate",
            json={"model": modelo, "keep_alive": 0},
            timeout=60,
        )


def medir(
    cliente: ClienteLLM,
    variante: str | prompts.Prompt,
    casos: list[tickets.Ticket],
    opciones: Opciones = OPCIONES,
    aislar: bool = True,
) -> Medida:
    """Mide un prompt: por nombre (`tickets/completo`) o ya cargado."""
    if aislar:
        empezar_de_cero(cliente)
    prompt = prompts.cargar(variante) if isinstance(variante, str) else variante
    medida = Medida(variante=prompt.id)
    for caso in casos:
        r = cliente.chat(prompts.renderizar(prompt, ticket=caso.texto), opciones=opciones)
        predicha = tickets.leer_lineas(r.texto)
        acierto = tickets.aciertos(predicha, caso.esperado)
        medida.utilizables += predicha is not None
        for campo, bien in acierto.items():
            medida.aciertos[campo] += bien
        medida.todo_bien += all(acierto.values())
        medida.tokens_entrada += r.tokens_entrada
        medida.tokens_salida += r.tokens_salida
        medida.latencia += r.latencia_s
        medida.ejemplo = medida.ejemplo or r.texto.strip()
        medida.predicciones.append(predicha)
        e = caso.esperado
        estado = "OK  " if all(acierto.values()) else ("NULO" if predicha is None else "MAL ")
        respuesta = " / ".join(r.texto.strip().splitlines()[-3:])
        medida.detalle.append(
            f"{caso.id:3} {estado} esperado {e.categoria}/{e.severidad}/{e.servicio} -> {respuesta}"
        )
    return medida


def tabla(medidas: list[Medida], n: int) -> None:
    print(f"{'variante':26} {'utilizables':>11} {'categoría':>9} {'severidad':>9} ", end="")
    print(f"{'servicio':>8} {'las 3':>5} {'tokens':>6} {'latencia':>8}")
    for m in medidas:
        a = m.aciertos
        print(
            f"{m.variante:26} {m.utilizables:>8}/{n} {a['categoria']:>7}/{n} "
            f"{a['severidad']:>7}/{n} {a['servicio']:>6}/{n} {m.todo_bien:>3}/{n} "
            f"{m.tokens_entrada // n:>6} {m.latencia / n:>7.2f}s"
        )
    print("\n(tokens: entrada media por ticket · latencia: media por ticket)")

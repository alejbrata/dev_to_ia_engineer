"""El bucle de un agente, sin framework (lección 03).

En cada paso, el modelo recibe la conversación hasta ahora y responde con texto o con
llamadas a herramientas. Si pide herramientas, el código las ejecuta y le devuelve los
resultados; si responde con texto, ha terminado. Un límite de pasos evita los bucles
infinitos. Cada paso queda registrado (herramientas, tokens, tiempo) para poder medirlo.
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from curso_core import ClienteLLM, Herramienta, Mensaje, Opciones, PromptRenderizado, prompts
from plataforma import HERRAMIENTAS, Plataforma
from pydantic import BaseModel

OPCIONES = Opciones(temperatura=0, max_tokens=800)
MAX_PASOS = 10
ROL = "agente"  # el modelo local del módulo, elegido midiendo en la lección 02


def argumento_rol(parser: argparse.ArgumentParser) -> None:
    """La opción --rol de las prácticas: repetirlas con otro modelo, sin tocar el código."""
    parser.add_argument(
        "--rol",
        default=ROL,
        help="el modelo, como rol de config/models.toml: por defecto el local; por ejemplo "
        "chat_openai, chat_claude o chat_hf (necesitan su clave en .env y cuestan dinero)",
    )


def usar_rol(rol: str, resultados: Path) -> Path:
    """Hace que el rol `agente` sea `rol` en todo el proceso (CURSO_ROLES, en curso_core) y
    devuelve dónde guardar: con otro modelo, en `resultados/<rol>/`, para no pisar los
    resultados de las lecciones."""
    if rol == ROL:
        return resultados
    os.environ["CURSO_ROLES"] = f"{ROL}={rol}"
    return resultados / rol


class Uso(BaseModel):
    """Una herramienta usada en un paso: qué pidió el modelo y qué le devolvió el código."""

    nombre: str
    argumentos: dict
    resultado: str
    valida: bool


class Paso(BaseModel):
    n: int
    texto: str
    usos: list[Uso] = []
    tokens_entrada: int
    tokens_salida: int
    segundos: float
    coste_usd: float = 0.0  # 0 con modelos locales; con una API comercial, lo que costó


class Ejecucion(BaseModel):
    pasos: list[Paso]
    respuesta: str
    terminacion: Literal["respuesta", "limite_pasos", "presupuesto"]

    @property
    def tokens(self) -> int:
        return sum(p.tokens_entrada + p.tokens_salida for p in self.pasos)

    @property
    def segundos(self) -> float:
        return sum(p.segundos for p in self.pasos)

    @property
    def coste_usd(self) -> float:
        return sum(p.coste_usd for p in self.pasos)

    @property
    def usos(self) -> list[Uso]:
        return [u for p in self.pasos for u in p.usos]


def ejecutar(
    cliente: ClienteLLM,
    plataforma: Plataforma,
    *,
    rol: str = "chat",
    prompt: str = "agentes/guardia",
    max_pasos: int = MAX_PASOS,
    opciones: Opciones = OPCIONES,
    herramientas: list[Herramienta] = HERRAMIENTAS,
    variables: dict[str, str] | None = None,
    contexto: Callable[[list[Mensaje]], list[Mensaje]] | None = None,
    paralelo: bool = False,
    historial: list[Mensaje] | None = None,
    al_terminar_paso: Callable[[list[Mensaje]], None] | None = None,
    presupuesto_tokens: int | None = None,
) -> Ejecucion:
    """Ejecuta el bucle. `variables` rellena el prompt (por defecto, la alerta del escenario).
    `contexto`, si se pasa, decide qué parte de la conversación ve el modelo en cada paso
    (lección 07); la conversación completa se conserva igual. Con `paralelo`, las herramientas
    que el modelo pide en un mismo paso se ejecutan a la vez (lección 08).

    Para aguantar fallos (lección 13): `historial` reanuda una conversación guardada,
    `al_terminar_paso` recibe la conversación tras cada paso (para guardar un checkpoint) y
    `presupuesto_tokens` corta la ejecución cuando los tokens gastados lo superan."""
    variables = variables or {"alerta": plataforma.escenario.alerta}
    renderizado = prompts.renderizar(prompts.cargar(prompt), **variables)
    mensajes = list(historial) if historial else list(renderizado.mensajes)
    opciones = opciones.model_copy(update={"herramientas": herramientas})
    pasos: list[Paso] = []
    for n in range(1, max_pasos + 1):
        inicio = time.perf_counter()
        # PromptRenderizado conserva el id del prompt en las trazas de cada llamada.
        r = cliente.chat(
            PromptRenderizado(
                id=renderizado.id, mensajes=contexto(mensajes) if contexto else mensajes
            ),
            rol=rol,
            opciones=opciones,
        )
        paso = Paso(
            n=n,
            texto=r.texto.strip(),
            tokens_entrada=r.tokens_entrada,
            tokens_salida=r.tokens_salida,
            segundos=0.0,
            coste_usd=r.coste_usd or 0.0,
        )
        if not r.llamadas:
            paso.segundos = time.perf_counter() - inicio
            pasos.append(paso)
            return Ejecucion(pasos=pasos, respuesta=paso.texto, terminacion="respuesta")
        mensajes.append(r.como_mensaje())
        if paralelo and len(r.llamadas) > 1:
            with ThreadPoolExecutor() as pool:
                ejecutadas = list(pool.map(plataforma.ejecutar, r.llamadas))
        else:
            ejecutadas = [plataforma.ejecutar(llamada) for llamada in r.llamadas]
        for llamada, (resultado, valida) in zip(r.llamadas, ejecutadas, strict=True):
            paso.usos.append(
                Uso(
                    nombre=llamada.nombre,
                    argumentos=llamada.argumentos,
                    resultado=resultado,
                    valida=valida,
                )
            )
            mensajes.append(Mensaje(role="tool", content=resultado, respuesta_a=llamada))
        paso.segundos = time.perf_counter() - inicio
        pasos.append(paso)
        if al_terminar_paso:
            al_terminar_paso(mensajes)
        gastado = sum(x.tokens_entrada + x.tokens_salida for x in pasos)
        if presupuesto_tokens is not None and gastado > presupuesto_tokens:
            return Ejecucion(pasos=pasos, respuesta="", terminacion="presupuesto")
    return Ejecucion(pasos=pasos, respuesta="", terminacion="limite_pasos")

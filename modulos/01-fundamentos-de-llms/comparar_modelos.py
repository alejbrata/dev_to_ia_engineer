"""Tres tamaños de la misma familia de modelos, con las mismas preguntas.

Mide, para cada modelo, cuántas respuestas acierta, cuánto tarda, a qué velocidad
genera y cuánta memoria ocupa. Las preguntas tienen una respuesta comprobable: es
una evaluación en miniatura, que ampliarás en los módulos 2 y 4.

Uso: `uv run python modulos/01-fundamentos-de-llms/comparar_modelos.py`
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable

import httpx
from curso_core import ClienteLLM, Opciones
from curso_core import config as cfg
from pydantic import BaseModel

ROLES = ["chat_pequeno", "chat", "chat_grande"]


class Pregunta(BaseModel):
    texto: str
    # Comprueba la respuesta (en minúsculas). Una función, no un texto exacto.
    acierta: Callable[[str], bool]


def contiene(*palabras: str) -> Callable[[str], bool]:
    return lambda r: all(p in r for p in palabras)


def alguna(*palabras: str) -> Callable[[str], bool]:
    return lambda r: any(p in r for p in palabras)


PREGUNTAS = [
    Pregunta(
        texto="Completa con una sola palabra: el cielo despejado es de color",
        acierta=contiene("azul"),
    ),
    Pregunta(
        texto="¿Cuál es la capital de Australia? Responde solo con el nombre.",
        acierta=contiene("canberra"),
    ),
    Pregunta(texto="¿Cuánto es 17 × 23? Responde solo con el número.", acierta=contiene("391")),
    Pregunta(
        texto="En una arquitectura web, ¿para qué sirve un balanceador de carga? Una frase.",
        acierta=alguna("servidor", "peticion", "petición", "tráfico", "solicitud"),
    ),
    Pregunta(
        texto="Traduce al inglés, solo la traducción: La cola de mensajes desacopla los servicios.",
        acierta=contiene("queue", "decouple"),
    ),
]


class Resultado(BaseModel):
    modelo: str
    aciertos: int
    latencia_media_s: float
    tokens_por_segundo: float
    memoria_gb: float


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.lower()).strip()


def memoria_gb(base_url: str, modelo: str) -> float:
    cargados = httpx.get(f"{base_url}/api/ps", timeout=10).json()["models"]
    return next((m["size"] / 1e9 for m in cargados if m["name"] == modelo), 0.0)


def evaluar(cliente: ClienteLLM, rol: str, base_url: str, modelo: str) -> Resultado:
    # Una llamada de calentamiento para no medir la carga del modelo en la primera pregunta.
    cliente.chat("Hola.", rol=rol, opciones=Opciones(max_tokens=1))
    aciertos, latencias, tokens, tiempo_generacion = 0, [], 0, 0.0
    print(f"\n[{modelo}]")
    for pregunta in PREGUNTAS:
        r = cliente.chat(pregunta.texto, rol=rol, opciones=Opciones(temperatura=0, max_tokens=80))
        bien = pregunta.acierta(normalizar(r.texto))
        aciertos += bien
        latencias.append(r.latencia_s)
        tokens += r.tokens_salida
        tiempo_generacion += r.latencia_s
        print(f"  {'OK   ' if bien else 'FALLO'} {r.latencia_s:5.1f} s  {r.texto.strip()[:70]!r}")
    return Resultado(
        modelo=modelo,
        aciertos=aciertos,
        latencia_media_s=sum(latencias) / len(latencias),
        tokens_por_segundo=tokens / tiempo_generacion,
        memoria_gb=memoria_gb(base_url, modelo),
    )


def main() -> int:
    config = cfg.cargar()
    cliente = ClienteLLM(config)
    resultados = []
    for rol in ROLES:
        _, proveedor, modelo = config.resolver(rol)
        resultados.append(evaluar(cliente, rol, proveedor.base_url, modelo))

    print(f"\n{'modelo':16} {'aciertos':>9} {'latencia media':>15} {'tokens/s':>9} {'memoria':>8}")
    for r in resultados:
        print(
            f"{r.modelo:16} {r.aciertos:>4} de {len(PREGUNTAS)} {r.latencia_media_s:>13.1f} s"
            f" {r.tokens_por_segundo:>9.1f} {r.memoria_gb:>6.2f} GB"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

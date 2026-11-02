"""La API del asistente de documentación (módulo 6).

- POST /preguntas: responde en la misma petición (síncrono). Para preguntas sueltas.
- POST /trabajos y GET /trabajos/{id}: encola la pregunta y responde al momento con un
  id; un trabajador la procesa y el cliente consulta el resultado después. Para lotes o
  para cuando el cliente no puede esperar con la conexión abierta.
- GET /salud: si el servicio está en marcha y con qué versión del sistema.
- GET /metrics: las métricas en formato Prometheus (lección 6.03, metricas_servicio.py).

Configuración por variables de entorno: ASISTENTE_CACHE=0 desactiva la caché;
ASISTENTE_TRAZAS=1 activa las trazas de OpenTelemetry (lección 6.02, observabilidad.py);
ASISTENTE_GUARDRAILS=1 activa los guardrails de entrada y salida (lección 6.05).
Arranque: `uv run uvicorn servicio:app --app-dir modulos/06-produccion --port 8100`
"""

from __future__ import annotations

import os
import queue
import threading
import uuid
from contextlib import asynccontextmanager
from typing import Literal

import metricas_servicio
from asistente import Asistente, Resultado
from curso_core import tracing
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=3, max_length=1000)


class Trabajo(BaseModel):
    id: str
    estado: Literal["pendiente", "hecho"]
    resultado: Resultado | None = None


estado: dict = {}


def trabajador() -> None:
    """Procesa la cola de uno en uno. En producción, una cola externa (Redis, RabbitMQ,
    SQS) con varios trabajadores, para que los trabajos sobrevivan a un reinicio."""
    while True:
        trabajo, pregunta = estado["cola"].get()
        trabajo.resultado = estado["asistente"].responder(pregunta)
        metricas_servicio.observar_pregunta(trabajo.resultado)
        trabajo.estado = "hecho"


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    trazas = None
    if os.environ.get("ASISTENTE_TRAZAS") == "1":
        import observabilidad

        trazas = observabilidad.configurar()
    # Construir el índice tarda unos segundos: se hace una vez, al arrancar.
    estado["asistente"] = Asistente(
        cache=os.environ.get("ASISTENTE_CACHE", "1") != "0",
        guardrails=os.environ.get("ASISTENTE_GUARDRAILS") == "1",
    )
    estado["cola"], estado["trabajos"] = queue.Queue(), {}
    threading.Thread(target=trabajador, daemon=True).start()
    tracing.observadores.append(metricas_servicio.observar_llamada)
    yield
    tracing.observadores.remove(metricas_servicio.observar_llamada)
    if trazas:
        trazas.shutdown()  # envía los spans que quedan en el búfer antes de salir


app = FastAPI(title="Asistente de documentación interna", lifespan=ciclo_de_vida)
app.mount("/metrics", make_asgi_app())


@app.post("/preguntas")
def preguntar(p: Pregunta) -> Resultado:
    # Una función normal (no async): FastAPI la ejecuta en un hilo aparte, así que una
    # llamada lenta al modelo no bloquea al resto de peticiones.
    # Con las trazas activas, FastAPI abre él mismo el span de la petición (POST /preguntas,
    # con método, ruta y código de respuesta): el del asistente cuelga de ese.
    resultado = estado["asistente"].responder(p.pregunta)
    metricas_servicio.observar_pregunta(resultado)
    return resultado


@app.post("/trabajos", status_code=202)
def encolar(p: Pregunta) -> Trabajo:
    trabajo = Trabajo(id=uuid.uuid4().hex[:12], estado="pendiente")
    estado["trabajos"][trabajo.id] = trabajo
    estado["cola"].put((trabajo, p.pregunta))
    return trabajo


@app.get("/trabajos/{id}")
def consultar(id: str) -> Trabajo:
    if id not in estado["trabajos"]:
        raise HTTPException(status_code=404, detail="No existe ese trabajo")
    return estado["trabajos"][id]


@app.get("/salud")
def salud() -> dict:
    a = estado["asistente"]
    cache = {"aciertos": a.cache.aciertos, "fallos": a.cache.fallos} if a.cache else None
    return {"estado": "ok", "version": a.version, "roles": a.roles, "cache": cache}

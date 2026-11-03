"""La API del asistente de documentación (módulo 6).

- POST /preguntas: responde en la misma petición (síncrono). Para preguntas sueltas.
- POST /trabajos y GET /trabajos/{id}: encola la pregunta y responde al momento con un
  id; un trabajador la procesa y el cliente consulta el resultado después. Para lotes o
  para cuando el cliente no puede esperar con la conexión abierta.
- GET /salud: si el servicio está en marcha y con qué versión del sistema.
- POST /valoraciones: el 👍 o 👎 de un usuario a una respuesta, por su id (lección 6.10).
- GET /metrics: las métricas en formato Prometheus (lección 6.03, metricas_servicio.py).

Configuración por variables de entorno: ASISTENTE_CACHE=0 desactiva la caché;
ASISTENTE_TRAZAS=1 activa las trazas de OpenTelemetry (lección 6.02, observabilidad.py);
ASISTENTE_GUARDRAILS=1 activa los guardrails de entrada y salida (lección 6.05);
ASISTENTE_CALIDAD=0.1 juzga en segundo plano el 10 % de las respuestas generadas y publica
su fidelidad, relevancia y precisión del contexto en /metrics (lección 6.09, calidad.py);
ASISTENTE_VALORACIONES=<fichero> guarda las valoraciones en JSONL para revisarlas (6.10).
Arranque: `uv run uvicorn servicio:app --app-dir modulos/06-produccion --port 8100`
"""

from __future__ import annotations

import os
import queue
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import feedback
import metricas_servicio
from asistente import Asistente, Resultado
from curso_core import ClienteLLM, tracing
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
        trabajo.resultado = responder(pregunta)
        trabajo.estado = "hecho"


def responder(pregunta: str) -> Resultado:
    a = estado["asistente"]
    # Un id por respuesta servida, también si sale de la caché: es lo que el usuario valora.
    resultado = a.responder(pregunta).model_copy(update={"id": uuid.uuid4().hex[:16]})
    metricas_servicio.observar_pregunta(resultado)
    # La versión, como etiqueta de Prometheus: el modelo principal (pocas combinaciones).
    version = a.modelos[a.roles[0]]
    estado["registro"].guardar(resultado.id, pregunta, resultado, version)
    if estado["calidad"]:
        estado["calidad"].enviar(pregunta, resultado, version=version)
    return resultado


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
    ruta = os.environ.get("ASISTENTE_VALORACIONES")
    estado["registro"] = feedback.Registro(ruta=Path(ruta) if ruta else None)
    estado["calidad"] = None
    if muestreo := float(os.environ.get("ASISTENTE_CALIDAD", "0")):
        import calidad
        import sistema

        estado["calidad"] = calidad.EvaluadorEnLinea(
            ClienteLLM(),
            sistema.fragmentos(),
            muestreo,
            al_evaluar=metricas_servicio.observar_calidad,
        )
    threading.Thread(target=trabajador, daemon=True).start()
    tracing.observadores.append(metricas_servicio.observar_llamada)
    yield
    tracing.observadores.remove(metricas_servicio.observar_llamada)
    if estado["calidad"]:
        estado["calidad"].esperar()
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
    return responder(p.pregunta)


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


@app.post("/valoraciones", status_code=201)
def valorar(v: feedback.Valoracion) -> dict:
    fila = estado["registro"].valorar(v)
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe esa respuesta o ya caducó")
    metricas_servicio.observar_valoracion(fila["version"], v.util)
    return {"id": v.id, "registrada": True}


@app.get("/salud")
def salud() -> dict:
    a = estado["asistente"]
    cache = {"aciertos": a.cache.aciertos, "fallos": a.cache.fallos} if a.cache else None
    return {
        "estado": "ok",
        "version": a.version,
        "modelos": a.modelos,
        "roles": a.roles,
        "cache": cache,
    }

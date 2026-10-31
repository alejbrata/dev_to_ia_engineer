"""El agente de guardia como workflow: los pasos los fija el código, no el modelo (lección 01).

1. El modelo dice a qué servicio afecta la alerta.
2. El código recoge, siempre igual, el estado del servicio, sus logs y la documentación
   relevante (la búsqueda con la alerta y la de los criterios de severidad).
3. El modelo decide si abrir incidencia, con qué severidad y con qué mitigación, y el
   código la abre.

Dos llamadas al modelo por alerta, siempre. Las mismas herramientas que el agente.
"""

from __future__ import annotations

import time

from curso_core import ClienteLLM, ErrorFormato, Opciones, prompts
from plataforma import ArgsBuscar, ArgsLogs, ArgsServicio, Incidencia, Plataforma, Servicio
from plataforma import Severidad as SeveridadIncidencia
from pydantic import BaseModel

OPCIONES = Opciones(temperatura=0, max_tokens=400)


class ServicioAfectado(BaseModel):
    servicio: Servicio


class Decision(BaseModel):
    abrir: bool
    severidad: SeveridadIncidencia | None = None
    resumen: str
    mitigacion: str


class EjecucionWorkflow(BaseModel):
    llamadas_modelo: int
    tokens: int
    segundos: float
    decision: Decision | None
    error: str | None = None


def ejecutar(
    cliente: ClienteLLM, plataforma: Plataforma, *, rol: str = "chat"
) -> EjecucionWorkflow:
    alerta = plataforma.escenario.alerta
    inicio = time.perf_counter()
    tokens = llamadas = 0
    try:
        mensajes = prompts.renderizar(prompts.cargar("agentes/workflow-servicio"), alerta=alerta)
        afectado, r = cliente.extraer(mensajes, ServicioAfectado, rol=rol, opciones=OPCIONES)
        tokens, llamadas = r.tokens_entrada + r.tokens_salida, 1

        servicio = afectado.servicio
        estado = plataforma.estado_servicio(ArgsServicio(servicio=servicio))
        logs = plataforma.buscar_logs(ArgsLogs(servicio=servicio))
        documentacion = "\n\n".join(
            plataforma.buscar_documentacion(ArgsBuscar(consulta=c))
            for c in [f"{alerta}\n{logs}", "criterios de severidad de las incidencias"]
        )
        mensajes = prompts.renderizar(
            prompts.cargar("agentes/workflow-decision"),
            alerta=alerta,
            estado=estado,
            logs=logs,
            documentacion=documentacion,
        )
        decision, r = cliente.extraer(mensajes, Decision, rol=rol, opciones=OPCIONES)
        tokens, llamadas = tokens + r.tokens_entrada + r.tokens_salida, 2
    except ErrorFormato as e:
        return EjecucionWorkflow(
            llamadas_modelo=llamadas + 1,
            tokens=tokens,
            segundos=time.perf_counter() - inicio,
            decision=None,
            error=str(e)[:200],
        )
    if decision.abrir and decision.severidad is not None:
        plataforma.abrir_incidencia(
            Incidencia(
                servicio=servicio,
                severidad=decision.severidad,
                resumen=decision.resumen,
                mitigacion=decision.mitigacion,
            )
        )
    return EjecucionWorkflow(
        llamadas_modelo=llamadas,
        tokens=tokens,
        segundos=time.perf_counter() - inicio,
        decision=decision,
    )

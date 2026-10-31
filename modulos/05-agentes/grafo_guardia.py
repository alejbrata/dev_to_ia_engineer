"""El agente de guardia como grafo de estado (lecciones 05 y 06).

    clasificar → recoger → decidir ─┬─ (error, quedan intentos) → decidir
                                    ├─ (abrir) → [aprobación humana] → abrir → FIN
                                    └─ (no abrir, o sin intentos) → FIN

Los pasos son los del workflow de la lección 01, con tres añadidos: un ciclo que repite la
decisión si el modelo devuelve algo que no se puede leer, un checkpoint tras cada nodo y una
parada antes de abrir la incidencia para que una persona la apruebe o la corrija.

Los nodos y la condición no dependen del motor: la lección 05 los ejecuta con `grafo.py` y
la 06, sin cambiarlos, con LangGraph.
"""

from __future__ import annotations

from curso_core import ClienteLLM, ErrorFormato, prompts
from grafo import FIN, Grafo
from plataforma import ArgsBuscar, ArgsLogs, ArgsServicio, Incidencia, Plataforma, Servicio
from pydantic import BaseModel
from workflow import OPCIONES, Decision, ServicioAfectado

MAX_INTENTOS = 3
DESTINOS_DECIDIR = {"decidir", "abrir", FIN}


class EstadoGuardia(BaseModel):
    alerta: str
    servicio: Servicio | None = None
    estado_servicio: str = ""
    logs: str = ""
    documentacion: str = ""
    decision: Decision | None = None
    intentos: int = 0
    error: str | None = None
    # Lo que decide la persona en la aprobación: None mientras no ha decidido.
    aprobada: bool | None = None
    incidencia: str | None = None
    llamadas_modelo: int = 0
    tokens: int = 0


class NodosGuardia:
    def __init__(self, cliente: ClienteLLM, plataforma: Plataforma, *, rol: str = "agente"):
        self.cliente = cliente
        self.plataforma = plataforma
        self.rol = rol

    def clasificar(self, e: EstadoGuardia) -> dict:
        mensajes = prompts.renderizar(prompts.cargar("agentes/workflow-servicio"), alerta=e.alerta)
        afectado, r = self.cliente.extraer(
            mensajes, ServicioAfectado, rol=self.rol, opciones=OPCIONES
        )
        return {
            "servicio": afectado.servicio,
            "llamadas_modelo": e.llamadas_modelo + 1,
            "tokens": e.tokens + r.tokens_entrada + r.tokens_salida,
        }

    def recoger(self, e: EstadoGuardia) -> dict:
        p = self.plataforma
        logs = p.buscar_logs(ArgsLogs(servicio=e.servicio))
        consultas = [f"{e.alerta}\n{logs}", "criterios de severidad de las incidencias"]
        return {
            "estado_servicio": p.estado_servicio(ArgsServicio(servicio=e.servicio)),
            "logs": logs,
            "documentacion": "\n\n".join(
                p.buscar_documentacion(ArgsBuscar(consulta=c)) for c in consultas
            ),
        }

    def decidir(self, e: EstadoGuardia) -> dict:
        mensajes = prompts.renderizar(
            prompts.cargar("agentes/workflow-decision"),
            alerta=e.alerta,
            estado=e.estado_servicio,
            logs=e.logs,
            documentacion=e.documentacion,
        )
        cambios = {"intentos": e.intentos + 1, "llamadas_modelo": e.llamadas_modelo + 1}
        try:
            decision, r = self.cliente.extraer(mensajes, Decision, rol=self.rol, opciones=OPCIONES)
        except ErrorFormato as error:
            r = error.respuesta
            return cambios | {
                "error": str(error)[:200],
                "tokens": e.tokens + r.tokens_entrada + r.tokens_salida,
            }
        return cambios | {
            "decision": decision,
            "error": None,
            "tokens": e.tokens + r.tokens_entrada + r.tokens_salida,
        }

    def abrir(self, e: EstadoGuardia) -> dict:
        if e.aprobada is False:
            return {"incidencia": "rechazada en la aprobación"}
        d = e.decision
        texto = self.plataforma.abrir_incidencia(
            Incidencia(
                servicio=e.servicio,
                severidad=d.severidad,
                resumen=d.resumen,
                mitigacion=d.mitigacion,
            )
        )
        return {"incidencia": texto}


def tras_decidir(e: EstadoGuardia) -> str:
    if e.error is not None:
        return "decidir" if e.intentos < MAX_INTENTOS else FIN
    if e.decision.abrir and e.decision.severidad is not None:
        return "abrir"
    return FIN


def construir(nodos: NodosGuardia) -> Grafo[EstadoGuardia]:
    g = Grafo(EstadoGuardia, inicio="clasificar")
    g.nodo("clasificar", nodos.clasificar)
    g.nodo("recoger", nodos.recoger)
    g.nodo("decidir", nodos.decidir)
    g.nodo("abrir", nodos.abrir)
    g.arista("clasificar", "recoger")
    g.arista("recoger", "decidir")
    g.arista_condicional("decidir", tras_decidir, DESTINOS_DECIDIR)
    g.arista("abrir", FIN)
    return g

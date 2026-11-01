"""Un sistema multiagente desde cero: investigador, revisor y coordinador (lección 09).

Tres papeles alrededor de una pizarra compartida (un objeto con todo lo que se sabe):

- El investigador es el bucle de la lección 03 con las herramientas de lectura y una más,
  `proponer_incidencia`. No abre nada: deja su propuesta en la pizarra. Cada resultado de
  herramienta queda también en la pizarra, tal cual, como evidencia.
- El revisor es una llamada con salida estructurada. Lee la propuesta, los criterios de
  severidad completos y, si se le dan, las evidencias en bruto. Decide si está de acuerdo
  y, si no, corrige la severidad, la mitigación o si hay que abrir.
- El coordinador es código, no un modelo: aplica la decisión final y abre la incidencia.
  Así, que la incidencia se abra no depende de que un modelo se acuerde de hacerlo.

Si el investigador termina sin proponer (el "dice sin hacer" de la lección 07), un último
paso convierte su respuesta en una propuesta estructurada.
"""

from __future__ import annotations

import time

import agente
import corpus
from curso_core import ClienteLLM, ErrorFormato, Herramienta, LlamadaHerramienta, Opciones, prompts
from plataforma import HERRAMIENTAS, Incidencia, Plataforma, Servicio, Severidad
from pydantic import BaseModel, Field, ValidationError

OPCIONES = Opciones(temperatura=0, max_tokens=800, razonar=False)
LECTURA = [h for h in HERRAMIENTAS if h.nombre != "abrir_incidencia"]
DESCRIPCION_SEVERIDAD = next(h for h in HERRAMIENTAS if h.nombre == "abrir_incidencia").parametros[
    "properties"
]["severidad"]["description"]


class Propuesta(BaseModel):
    abrir: bool = Field(description="Si hace falta abrir una incidencia.")
    servicio: Servicio = Field(description="El servicio afectado.")
    severidad: Severidad | None = Field(None, description=DESCRIPCION_SEVERIDAD)
    resumen: str = Field(description="La causa, en una o dos frases, según logs y estado.")
    mitigacion: str = Field(description="La acción concreta que indica el runbook.")


class Revision(BaseModel):
    de_acuerdo: bool = Field(description="True si la propuesta es correcta tal cual.")
    abrir: bool = Field(description="Si hace falta abrir una incidencia.")
    # Sin valor por defecto: el modelo tiene que escribirla siempre (null solo si no se abre).
    severidad: Severidad | None = Field(
        description="La severidad correcta según los criterios. Obligatoria si abrir es true."
    )
    mitigacion: str = Field(description="La mitigación correcta según el runbook.")
    motivo: str = Field(description="Qué criterio o qué evidencia justifica la decisión.")


class Evaluacion(BaseModel):
    """La revisión a ciegas: el revisor decide sin ver la propuesta."""

    abrir: bool = Field(description="Si hace falta abrir una incidencia.")
    severidad: Severidad | None = Field(
        description="La severidad según los criterios. Obligatoria si abrir es true."
    )
    motivo: str = Field(description="Qué criterio se cumple y qué evidencia lo muestra.")


class Evidencia(BaseModel):
    herramienta: str
    argumentos: dict
    resultado: str


class Pizarra(BaseModel):
    alerta: str
    evidencias: list[Evidencia] = []
    propuesta: Propuesta | None = None
    redactada: bool = False  # la propuesta salió de la respuesta final, no de la herramienta
    revision: Revision | None = None


PROPONER = Herramienta.desde(
    "proponer_incidencia",
    "Deja tu propuesta para que la revise otra persona: si hay que abrir una incidencia, con "
    "qué servicio, severidad y mitigación. Es la única forma de terminar tu trabajo; si no "
    "hace falta incidencia, propón abrir=false.",
    Propuesta,
)


class PlataformaInvestigador:
    """Lo que ve el investigador: las herramientas de lectura y proponer_incidencia."""

    def __init__(self, plataforma: Plataforma, pizarra: Pizarra):
        self.plataforma = plataforma
        self.escenario = plataforma.escenario
        self.pizarra = pizarra

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        if llamada.nombre == "proponer_incidencia":
            try:
                self.pizarra.propuesta = Propuesta.model_validate(llamada.argumentos)
            except ValidationError as e:
                return f"Error en la propuesta: {e.errors()[0]['msg']}", False
            return "Propuesta registrada. La revisará otra persona antes de abrir nada.", True
        if llamada.nombre == "abrir_incidencia":
            return "Error: no puedes abrir incidencias; usa proponer_incidencia.", False
        resultado, valida = self.plataforma.ejecutar(llamada)
        if valida:
            self.pizarra.evidencias.append(
                Evidencia(
                    herramienta=llamada.nombre, argumentos=llamada.argumentos, resultado=resultado
                )
            )
        return resultado, valida


class Uso(BaseModel):
    llamadas_modelo: int = 0
    tokens: int = 0

    def sumar(self, entrada: int, salida: int) -> None:
        self.llamadas_modelo += 1
        self.tokens += entrada + salida


def investigar(
    cliente: ClienteLLM, plataforma: Plataforma, *, rol: str, uso: Uso
) -> tuple[Pizarra, agente.Ejecucion]:
    pizarra = Pizarra(alerta=plataforma.escenario.alerta)
    ej = agente.ejecutar(
        cliente,
        PlataformaInvestigador(plataforma, pizarra),
        rol=rol,
        prompt="agentes/investigador",
        opciones=OPCIONES,
        herramientas=[*LECTURA, PROPONER],
    )
    for paso in ej.pasos:
        uso.sumar(paso.tokens_entrada, paso.tokens_salida)
    if pizarra.propuesta is None:
        # Terminó sin proponer: se estructura lo que escribió en su respuesta final.
        mensajes = prompts.renderizar(
            prompts.cargar("agentes/redactar-propuesta"),
            alerta=pizarra.alerta,
            respuesta=ej.respuesta or "(sin respuesta)",
        )
        try:
            propuesta, r = cliente.extraer(mensajes, Propuesta, rol=rol, opciones=OPCIONES)
            uso.sumar(r.tokens_entrada, r.tokens_salida)
            pizarra.propuesta, pizarra.redactada = propuesta, True
        except ErrorFormato as e:
            uso.sumar(e.respuesta.tokens_entrada, e.respuesta.tokens_salida)
    return pizarra, ej


def texto_evidencias(pizarra: Pizarra) -> str:
    return "\n\n".join(
        f"[{e.herramienta} {e.argumentos}]\n{e.resultado}" for e in pizarra.evidencias
    )


def revisar(
    cliente: ClienteLLM, pizarra: Pizarra, *, rol: str, con_evidencias: bool, uso: Uso
) -> Revision | None:
    evidencias = texto_evidencias(pizarra) if con_evidencias else "(no disponibles)"
    mensajes = prompts.renderizar(
        prompts.cargar("agentes/revisor"),
        alerta=pizarra.alerta,
        criterios=corpus.documentos()["severidades"],
        evidencias=evidencias or "(el investigador no consultó nada)",
        propuesta=pizarra.propuesta.model_dump_json(indent=2),
    )
    try:
        revision, r = cliente.extraer(mensajes, Revision, rol=rol, opciones=OPCIONES)
    except ErrorFormato as e:
        uso.sumar(e.respuesta.tokens_entrada, e.respuesta.tokens_salida)
        return None
    uso.sumar(r.tokens_entrada, r.tokens_salida)
    return revision


def revisar_a_ciegas(cliente: ClienteLLM, pizarra: Pizarra, *, rol: str) -> Evaluacion | None:
    """El revisor ve las evidencias y los criterios, pero no la propuesta: no puede anclarse."""
    mensajes = prompts.renderizar(
        prompts.cargar("agentes/revisor-ciego"),
        alerta=pizarra.alerta,
        criterios=corpus.documentos()["severidades"],
        evidencias=texto_evidencias(pizarra) or "(el investigador no consultó nada)",
    )
    try:
        evaluacion, _ = cliente.extraer(mensajes, Evaluacion, rol=rol, opciones=OPCIONES)
    except ErrorFormato:
        return None
    return evaluacion


def decision_a_ciegas(propuesta: Propuesta, evaluacion: Evaluacion | None) -> Propuesta:
    """El coordinador con revisión a ciegas: abrir y severidad del revisor; el resto, propuesta."""
    if evaluacion is None:
        return propuesta
    return propuesta.model_copy(
        update={
            "abrir": evaluacion.abrir,
            "severidad": evaluacion.severidad or propuesta.severidad,
        }
    )


def decision_final(propuesta: Propuesta, revision: Revision | None) -> Propuesta:
    """El coordinador: si el revisor no está de acuerdo, manda su corrección."""
    if revision is None or revision.de_acuerdo:
        return propuesta
    return propuesta.model_copy(
        update={
            "abrir": revision.abrir,
            # Si el revisor no da severidad, se queda la propuesta: sin ella no se abriría nada.
            "severidad": revision.severidad or propuesta.severidad,
            "mitigacion": revision.mitigacion or propuesta.mitigacion,
        }
    )


def aplicar(plataforma: Plataforma, decision: Propuesta | None) -> None:
    """El coordinador abre la incidencia; ningún modelo lo hace."""
    if decision is not None and decision.abrir and decision.severidad is not None:
        plataforma.abrir_incidencia(
            Incidencia(
                servicio=decision.servicio,
                severidad=decision.severidad,
                resumen=decision.resumen,
                mitigacion=decision.mitigacion,
            )
        )


class Resultado(BaseModel):
    pizarra: Pizarra
    revision_sin_evidencias: Revision | None
    pasos_investigador: int
    uso_investigador: Uso
    uso_revisor: Uso
    segundos: float


def ejecutar(cliente: ClienteLLM, plataforma: Plataforma, *, rol: str = "agente") -> Resultado:
    """Investiga una vez y revisa la misma propuesta dos veces: con y sin evidencias."""
    inicio, uso_inv, uso_rev = time.perf_counter(), Uso(), Uso()
    pizarra, ej = investigar(cliente, plataforma, rol=rol, uso=uso_inv)
    sin = None
    if pizarra.propuesta is not None:
        pizarra.revision = revisar(cliente, pizarra, rol=rol, con_evidencias=True, uso=uso_rev)
        segundos = time.perf_counter() - inicio  # el sistema completo, sin la variante de control
        sin = revisar(cliente, pizarra, rol=rol, con_evidencias=False, uso=Uso())
    else:
        segundos = time.perf_counter() - inicio
    return Resultado(
        pizarra=pizarra,
        revision_sin_evidencias=sin,
        pasos_investigador=len(ej.pasos),
        uso_investigador=uso_inv,
        uso_revisor=uso_rev,
        segundos=segundos,
    )

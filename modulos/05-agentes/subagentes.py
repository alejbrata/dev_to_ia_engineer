"""Subagentes: delegar con contexto aislado (lección 08).

El orquestador no toca logs ni documentación. Tiene dos herramientas que lanzan un
subagente cada una, más `abrir_incidencia`:

- `investigar(servicio, pregunta)`: un subagente con `estado_servicio` y `buscar_logs`.
- `consultar_documentacion(pregunta)`: un subagente con `buscar_documentacion`.

Cada subagente es el bucle de la lección 03 con su propio prompt, sus herramientas y una
conversación nueva. Al orquestador solo le llega su informe final: los resultados en bruto
de las herramientas se quedan en el contexto del subagente. Si el orquestador pide varias
delegaciones en un paso, pueden ejecutarse a la vez.
"""

from __future__ import annotations

import time

import agente
from curso_core import ClienteLLM, Herramienta, LlamadaHerramienta, Opciones
from plataforma import HERRAMIENTAS, Plataforma, Servicio
from pydantic import BaseModel, Field, ValidationError

MAX_PASOS_SUBAGENTE = 6
MAX_PASOS_ORQUESTADOR = 8
POR_NOMBRE = {h.nombre: h for h in HERRAMIENTAS}


class ArgsInvestigar(BaseModel):
    servicio: Servicio = Field(description="El servicio que hay que investigar.")
    pregunta: str = Field(
        description="Qué quieres saber de ese servicio (estado, errores, despliegues, logs)."
    )


class ArgsDocumentar(BaseModel):
    pregunta: str = Field(
        description="Qué necesitas de la documentación interna: el runbook de un problema "
        "concreto (con el error o el síntoma), los criterios de severidad, etc."
    )


class Subagente(BaseModel):
    prompt: str
    herramientas: list[str]
    argumentos: type[BaseModel]


SUBAGENTES = {
    "investigar": Subagente(
        prompt="agentes/subagente-investigador",
        herramientas=["estado_servicio", "buscar_logs"],
        argumentos=ArgsInvestigar,
    ),
    "consultar_documentacion": Subagente(
        prompt="agentes/subagente-documentacion",
        herramientas=["buscar_documentacion"],
        argumentos=ArgsDocumentar,
    ),
}
HERRAMIENTAS_ORQUESTADOR = [
    Herramienta.desde(
        "investigar",
        "Encarga a un ayudante que revise el estado y los logs de un servicio. Devuelve su "
        "informe. Puedes encargar varios a la vez, uno por servicio.",
        ArgsInvestigar,
    ),
    Herramienta.desde(
        "consultar_documentacion",
        "Encarga a un ayudante que busque en la documentación interna (runbooks, criterios "
        "de severidad, arquitectura). Devuelve lo que dice la documentación.",
        ArgsDocumentar,
    ),
    POR_NOMBRE["abrir_incidencia"],
]


class Delegacion(BaseModel):
    subagente: str
    tarea: str
    respuesta: str
    pasos: int
    tokens: int
    segundos: float
    terminacion: str
    usos: list[str]


class PlataformaRestringida:
    """La plataforma vista por un subagente: solo las herramientas que se le dieron. El
    modelo puede pedir otra (ha visto su nombre en otro sitio, o se la inventa); aquí se
    rechaza, no se confía en que no lo haga."""

    def __init__(self, plataforma: Plataforma, permitidas: list[str]):
        self.plataforma = plataforma
        self.escenario = plataforma.escenario
        self.permitidas = permitidas

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        if llamada.nombre not in self.permitidas:
            return f"Error: no tienes la herramienta {llamada.nombre!r}.", False
        return self.plataforma.ejecutar(llamada)


class PlataformaOrquestador:
    """Las herramientas del orquestador: delegar en subagentes y abrir la incidencia."""

    def __init__(
        self, cliente: ClienteLLM, plataforma: Plataforma, *, rol: str, opciones: Opciones
    ):
        self.cliente = cliente
        self.plataforma = plataforma
        self.escenario = plataforma.escenario
        self.rol = rol
        self.opciones = opciones
        self.delegaciones: list[Delegacion] = []

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        if llamada.nombre == "abrir_incidencia":
            return self.plataforma.ejecutar(llamada)
        sub = SUBAGENTES.get(llamada.nombre)
        if sub is None:
            return f"Error: no existe la herramienta {llamada.nombre!r}.", False
        try:
            args = sub.argumentos.model_validate(llamada.argumentos)
        except ValidationError as e:
            return f"Error en los argumentos: {e.errors()[0]['msg']}", False
        tarea = " ".join(f"{k}: {v}" for k, v in args.model_dump().items())
        inicio = time.perf_counter()
        ej = agente.ejecutar(
            self.cliente,
            PlataformaRestringida(self.plataforma, sub.herramientas),
            rol=self.rol,
            prompt=sub.prompt,
            max_pasos=MAX_PASOS_SUBAGENTE,
            opciones=self.opciones,
            herramientas=[POR_NOMBRE[h] for h in sub.herramientas],
            variables={"tarea": tarea},
        )
        respuesta = ej.respuesta or "El ayudante no terminó: agotó sus pasos sin informe."
        self.delegaciones.append(
            Delegacion(
                subagente=llamada.nombre,
                tarea=tarea,
                respuesta=respuesta,
                pasos=len(ej.pasos),
                tokens=ej.tokens,
                segundos=time.perf_counter() - inicio,
                terminacion=ej.terminacion,
                usos=[f"{u.nombre}({u.argumentos})" for u in ej.usos],
            )
        )
        return respuesta, True


class EjecucionOrquestada(BaseModel):
    orquestador: agente.Ejecucion
    delegaciones: list[Delegacion]
    segundos: float

    @property
    def tokens(self) -> int:
        return self.orquestador.tokens + sum(d.tokens for d in self.delegaciones)


def ejecutar(
    cliente: ClienteLLM,
    plataforma: Plataforma,
    *,
    rol: str,
    opciones: Opciones,
    paralelo: bool = True,
) -> EjecucionOrquestada:
    inicio = time.perf_counter()
    orq = PlataformaOrquestador(cliente, plataforma, rol=rol, opciones=opciones)
    ej = agente.ejecutar(
        cliente,
        orq,
        rol=rol,
        prompt="agentes/orquestador",
        max_pasos=MAX_PASOS_ORQUESTADOR,
        opciones=opciones,
        herramientas=HERRAMIENTAS_ORQUESTADOR,
        paralelo=paralelo,
    )
    return EjecucionOrquestada(
        orquestador=ej, delegaciones=orq.delegaciones, segundos=time.perf_counter() - inicio
    )

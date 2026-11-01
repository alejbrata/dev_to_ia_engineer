"""El cierre del módulo: un comité de crisis multiagente frente a un agente único (lección 15).

Incidentes que no son solo técnicos: un error de precios, una brecha de datos, cobros
duplicados, una caída en Black Friday. Cada uno pide decisiones de cuatro áreas, y cada área
tiene sus propias políticas (`datos/crisis/`).

- El agente único tiene todas las herramientas y busca en toda la documentación.
- El comité es un grafo de estado (lección 05): un orquestador planifica los encargos como un
  grafo de tareas (lección 04), cada especialista los resuelve con su documentación y sus
  herramientas (lecciones 08 y 11), un consolidador redacta el plan de respuesta y una
  persona lo aprueba antes de aplicarlo.
"""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Literal

import agente
import corpus
import grafo
from curso_core import ClienteLLM, ErrorFormato, Herramienta, LlamadaHerramienta, Opciones, prompts
from curso_core.rag import IndiceVectorial, trocear_por_secciones
from plataforma import (
    HERRAMIENTAS,
    ArgsBuscarV2,
    Escenario,
    Esperado,
    EstadoServicio,
    Plataforma,
    Servicio,
    Severidad,
)
from pydantic import BaseModel, Field, ValidationError
from subagentes import PlataformaRestringida

DATOS = Path(__file__).resolve().parent / "datos"
OPCIONES = Opciones(temperatura=0, max_tokens=1000, razonar=False)
Area = Literal["tecnico", "legal", "negocio", "comunicacion"]
AREAS: list[str] = ["tecnico", "legal", "negocio", "comunicacion"]
MAX_PASOS_ESPECIALISTA = 6


class Crisis(BaseModel):
    id: str
    alerta: str
    servicios: dict[Servicio, EstadoServicio] = {}
    logs: dict[Servicio, list[str]] = {}
    negocio: dict
    esperado: dict[str, list[str]]  # por área, alternativas "a|b" que el plan tiene que cubrir
    severidad: Severidad  # según los criterios del corpus (severidades.md)

    def como_escenario(self) -> Escenario:
        """Para reutilizar las herramientas de la plataforma (estado y logs)."""
        return Escenario(
            id=self.id,
            alerta=self.alerta,
            servicios=self.servicios,
            logs=self.logs,
            esperado=Esperado(incidencia=True, nota=""),
            particion="prueba",
        )


def cargar() -> list[Crisis]:
    with (DATOS / "crisis.jsonl").open(encoding="utf-8") as f:
        return [Crisis.model_validate_json(linea) for linea in f if linea.strip()]


def documentos(area: str | None = None) -> dict[str, str]:
    """Las políticas de un área (o todas). La técnica incluye además el corpus del módulo 3."""
    docs = {
        f.stem: f.read_text(encoding="utf-8")
        for f in sorted((DATOS / "crisis").glob("*.md"))
        if area is None or f.stem.startswith(area)
    }
    if area in (None, "tecnico"):
        docs |= corpus.documentos()
    return docs


def problemas_de_anclaje(crisis: list[Crisis]) -> list[str]:
    """Cada clave esperada tiene que salir de la documentación de su área."""
    problemas = []
    for c in crisis:
        for area, claves in c.esperado.items():
            texto = corpus.normalizar(" ".join(documentos(area).values()))
            for clave in claves:
                if not any(corpus.normalizar(a) in texto for a in clave.split("|")):
                    problemas.append(f"{c.id}: {clave!r} no sale de la documentación de {area}")
    return problemas


def indice(cliente: ClienteLLM, area: str | None) -> IndiceVectorial:
    i = IndiceVectorial(cliente)
    i.añadir([f for d, t in documentos(area).items() for f in trocear_por_secciones(d, t)])
    return i


# --- El plan de respuesta y cómo se puntúa ---------------------------------------------------


class PlanRespuesta(BaseModel):
    severidad: Severidad = Field(description="La severidad del incidente.")
    tecnico: list[str] = Field(description="Acciones técnicas, en orden.")
    legal: list[str] = Field(description="Obligaciones y acciones legales; vacía si no hay.")
    negocio: list[str] = Field(
        description="Decisiones de negocio: pedidos, reembolsos, compensaciones."
    )
    comunicacion: list[str] = Field(description="Qué se comunica, a quién y por qué canal.")


class Puntuacion(BaseModel):
    cubiertas: int
    total: int
    faltan: list[str]

    @property
    def completo(self) -> bool:
        return self.cubiertas == self.total


def puntuar(c: Crisis, plan: PlanRespuesta | None) -> Puntuacion:
    """¿Cubre el plan lo que piden las políticas? Cada clave, en cualquier parte del plan."""
    claves = [(area, clave) for area, cs in c.esperado.items() for clave in cs]
    if plan is None:
        return Puntuacion(cubiertas=0, total=len(claves), faltan=[f"{a}: {k}" for a, k in claves])
    texto = corpus.normalizar(" ".join(sum((getattr(plan, a) for a in AREAS), [])))
    faltan = [
        f"{a}: {k.split('|')[0]}"
        for a, k in claves
        if not any(corpus.normalizar(x) in texto for x in k.split("|"))
    ]
    return Puntuacion(cubiertas=len(claves) - len(faltan), total=len(claves), faltan=faltan)


# --- Herramientas -------------------------------------------------------------------------


class SinArgumentos(BaseModel):
    pass


DATOS_NEGOCIO = Herramienta.desde(
    "datos_negocio",
    "Devuelve los datos de negocio del incidente: pedidos, clientes o vendedores afectados, "
    "importes y si hay datos personales expuestos.",
    SinArgumentos,
)
BUSCAR = Herramienta.desde(
    "buscar_documentacion",
    "Busca en la documentación interna (runbooks y políticas) y devuelve los tres fragmentos "
    "más relevantes. Consulta la política o el runbook antes de recomendar una acción.",
    ArgsBuscarV2,
)
PROPONER_PLAN = Herramienta.desde(
    "proponer_plan",
    "Deja el plan de respuesta al incidente para que lo apruebe una persona. Es la única forma "
    "de terminar tu trabajo.",
    PlanRespuesta,
)
POR_NOMBRE = {h.nombre: h for h in [*HERRAMIENTAS, DATOS_NEGOCIO, BUSCAR, PROPONER_PLAN]}
HERRAMIENTAS_AREA = {
    "tecnico": ["estado_servicio", "buscar_logs", "buscar_documentacion"],
    "legal": ["buscar_documentacion", "datos_negocio"],
    "negocio": ["buscar_documentacion", "datos_negocio"],
    "comunicacion": ["buscar_documentacion", "datos_negocio"],
}
HERRAMIENTAS_UNICO = [
    "estado_servicio",
    "buscar_logs",
    "buscar_documentacion",
    "datos_negocio",
    "proponer_plan",
]


class PlataformaCrisis(Plataforma):
    """Las herramientas de la plataforma, más los datos de negocio y proponer el plan."""

    def __init__(self, crisis: Crisis, indice_docs: IndiceVectorial):
        super().__init__(crisis.como_escenario(), indice_docs)
        self.crisis = crisis
        self.plan: PlanRespuesta | None = None

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        if llamada.nombre == "datos_negocio":
            return json.dumps(self.crisis.negocio, ensure_ascii=False), True
        if llamada.nombre == "proponer_plan":
            try:
                self.plan = PlanRespuesta.model_validate(llamada.argumentos)
            except ValidationError as e:
                # Con el campo: sin él, el modelo no sabe qué corregir (lección 15, anatomía).
                error = e.errors()[0]
                campo = ".".join(str(p) for p in error["loc"]) or "argumentos"
                return f"Error en el plan ({campo}): {error['msg']}", False
            return "Plan registrado. Lo revisará una persona antes de aplicarlo.", True
        return super().ejecutar(llamada)


class Uso(BaseModel):
    llamadas_modelo: int = 0
    tokens: int = 0
    coste_usd: float = 0.0

    def de_ejecucion(self, ej: agente.Ejecucion) -> None:
        self.llamadas_modelo += len(ej.pasos)
        self.tokens += ej.tokens
        self.coste_usd += ej.coste_usd

    def de_respuesta(self, r) -> None:
        self.llamadas_modelo += 1
        self.tokens += r.tokens_entrada + r.tokens_salida
        self.coste_usd += r.coste_usd or 0.0


def extraer(cliente, prompt: str, modelo, *, rol: str, uso: Uso, **variables):
    mensajes = prompts.renderizar(prompts.cargar(prompt), **variables)
    try:
        resultado, r = cliente.extraer(mensajes, modelo, rol=rol, opciones=OPCIONES)
    except ErrorFormato as e:
        uso.de_respuesta(e.respuesta)
        return None
    uso.de_respuesta(r)
    return resultado


# --- El agente único ----------------------------------------------------------------------


class Resultado(BaseModel):
    plan: PlanRespuesta | None
    uso: Uso
    segundos: float
    detalle: dict = {}


def agente_unico(cliente, c: Crisis, indice_todo: IndiceVectorial, *, rol: str) -> Resultado:
    inicio, uso = time.perf_counter(), Uso()
    p = PlataformaCrisis(c, indice_todo)
    ej = agente.ejecutar(
        cliente,
        p,
        rol=rol,
        prompt="agentes/crisis-unico",
        opciones=OPCIONES,
        herramientas=[POR_NOMBRE[h] for h in HERRAMIENTAS_UNICO],
    )
    uso.de_ejecucion(ej)
    plan, redactado = p.plan, False
    if plan is None:
        # Sin un plan válido, se estructura lo que dejó (lección 09): su respuesta o, si agotó
        # los pasos insistiendo con un plan inválido, su último intento (anatomía de la 15).
        intentos = [u.argumentos for u in ej.usos if u.nombre == "proponer_plan"]
        ultimo = json.dumps(intentos[-1], ensure_ascii=False) if intentos else ""
        plan = extraer(
            cliente,
            "agentes/crisis-consolidar",
            PlanRespuesta,
            rol=rol,
            uso=uso,
            alerta=c.alerta,
            informes=ej.respuesta or ultimo or "(sin respuesta)",
        )
        redactado = True
    return Resultado(
        plan=plan,
        uso=uso,
        segundos=time.perf_counter() - inicio,
        detalle={"redactado": redactado, "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos]},
    )


# --- El comité ----------------------------------------------------------------------------


class Encargo(BaseModel):
    id: str
    especialista: Area
    pregunta: str
    depende_de: list[str] = []


class PlanEncargos(BaseModel):
    encargos: list[Encargo]


def problemas_plan(plan: PlanEncargos) -> list[str]:
    ids = [e.id for e in plan.encargos]
    errores = [] if len(set(ids)) == len(ids) else ["hay ids repetidos"]
    errores += [
        f"{e.id} depende de {d!r}, que no existe"
        for e in plan.encargos
        for d in e.depende_de
        if d not in ids
    ]
    if not errores and len(orden(plan)) != len(ids):
        errores.append("hay un ciclo en las dependencias")
    return errores


def orden(plan: PlanEncargos) -> list[str]:
    """Orden topológico (Kahn, lección 04)."""
    pendientes = {e.id: set(e.depende_de) for e in plan.encargos}
    listos = deque(i for i, d in pendientes.items() if not d)
    resultado = []
    while listos:
        actual = listos.popleft()
        resultado.append(actual)
        for i, deps in pendientes.items():
            if actual in deps:
                deps.discard(actual)
                if not deps and i not in resultado and i not in listos:
                    listos.append(i)
    return resultado


class EstadoComite(BaseModel):
    alerta: str
    encargos: PlanEncargos | None = None
    errores_plan: list[str] = []
    intentos_plan: int = 0
    informes: dict[str, str] = {}
    plan: PlanRespuesta | None = None
    aprobada: bool | None = None
    aplicado: bool = False


class Comite:
    """Los nodos del grafo del comité. Los modelos y los índices, por área."""

    def __init__(self, cliente, c: Crisis, indices: dict[str, IndiceVectorial], *, rol: str):
        self.cliente, self.c, self.indices, self.rol = cliente, c, indices, rol
        self.uso = Uso()
        self.ejecutados: list[dict] = []

    def planificar(self, e: EstadoComite) -> dict:
        errores = "\n".join(e.errores_plan) or "(ninguno)"
        plan = extraer(
            self.cliente,
            "agentes/crisis-orquestador",
            PlanEncargos,
            rol=self.rol,
            uso=self.uso,
            alerta=e.alerta,
            errores=errores,
        )
        errores_plan = ["el plan no se pudo leer"] if plan is None else problemas_plan(plan)
        return {
            "encargos": plan,
            "errores_plan": errores_plan,
            "intentos_plan": e.intentos_plan + 1,
        }

    def ejecutar(self, e: EstadoComite) -> dict:
        por_id = {x.id: x for x in e.encargos.encargos}
        informes = {}
        for i in orden(e.encargos):
            encargo = por_id[i]
            previos = "\n\n".join(
                f"[{d}, {por_id[d].especialista}] {informes[d]}" for d in encargo.depende_de
            )
            area = encargo.especialista
            p = PlataformaCrisis(self.c, self.indices[area])
            ej = agente.ejecutar(
                self.cliente,
                PlataformaRestringida(p, HERRAMIENTAS_AREA[area]),
                rol=self.rol,
                prompt="agentes/especialista",
                max_pasos=MAX_PASOS_ESPECIALISTA,
                opciones=OPCIONES,
                herramientas=[POR_NOMBRE[h] for h in HERRAMIENTAS_AREA[area]],
                variables={
                    "area": area,
                    "alerta": e.alerta,
                    "pregunta": encargo.pregunta,
                    "previos": previos or "(ninguno)",
                },
            )
            self.uso.de_ejecucion(ej)
            informes[i] = ej.respuesta or "(el especialista no terminó su informe)"
            self.ejecutados.append(
                {"id": i, "area": area, "pregunta": encargo.pregunta, "pasos": len(ej.pasos)}
            )
        return {"informes": informes}

    def consolidar(self, e: EstadoComite) -> dict:
        por_id = {x.id: x for x in e.encargos.encargos}
        texto = "\n\n".join(f"[{i}, {por_id[i].especialista}] {t}" for i, t in e.informes.items())
        plan = extraer(
            self.cliente,
            "agentes/crisis-consolidar",
            PlanRespuesta,
            rol=self.rol,
            uso=self.uso,
            alerta=e.alerta,
            informes=texto,
        )
        return {"plan": plan}

    def aplicar(self, e: EstadoComite) -> dict:
        return {"aplicado": bool(e.aprobada and e.plan)}


def tras_planificar(e: EstadoComite) -> str:
    if not e.errores_plan:
        return "ejecutar"
    return "planificar" if e.intentos_plan < 2 else grafo.FIN


def construir(comite: Comite) -> grafo.Grafo[EstadoComite]:
    g = grafo.Grafo(EstadoComite, inicio="planificar")
    g.nodo("planificar", comite.planificar)
    g.nodo("ejecutar", comite.ejecutar)
    g.nodo("consolidar", comite.consolidar)
    g.nodo("aplicar", comite.aplicar)
    g.arista_condicional("planificar", tras_planificar, {"planificar", "ejecutar", grafo.FIN})
    g.arista("ejecutar", "consolidar")
    g.arista("consolidar", "aplicar")
    g.arista("aplicar", grafo.FIN)
    return g


def comite(
    cliente, c: Crisis, indices: dict[str, IndiceVectorial], *, rol: str, checkpoints, aprobar
) -> Resultado:
    inicio = time.perf_counter()
    nodos = Comite(cliente, c, indices, rol=rol)
    g = construir(nodos)
    hilo = f"crisis-{c.id}-{rol}"
    r = g.ejecutar(
        EstadoComite(alerta=c.alerta),
        hilo=hilo,
        checkpoints=checkpoints,
        interrumpir_antes=frozenset({"aplicar"}),
    )
    if r.pendiente:  # la aprobación humana, antes de aplicar el plan
        r = g.ejecutar(None, hilo=hilo, checkpoints=checkpoints, cambios=aprobar(r.estado))
    e = r.estado
    return Resultado(
        plan=e.plan if e.aplicado else None,
        uso=nodos.uso,
        segundos=time.perf_counter() - inicio,
        detalle={
            "encargos": nodos.ejecutados,
            "errores_plan": e.errores_plan,
            "intentos_plan": e.intentos_plan,
            "informes": e.informes,
        },
    )

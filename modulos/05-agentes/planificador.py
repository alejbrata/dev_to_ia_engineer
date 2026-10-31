"""Un agente que planifica antes de actuar: el plan como grafo de tareas (lección 04).

1. Planificar: una llamada al modelo escribe el plan, una lista de tareas con dependencias.
   Una tarea puede usar el resultado de otra (`${t2}` en un argumento).
2. Validar: el código comprueba el plan antes de ejecutar nada (herramientas que existen,
   argumentos válidos, dependencias que existen, sin ciclos). Si falla, se replanifica con el
   error delante.
3. Ejecutar: el código recorre el grafo en orden topológico y pasa los resultados.
4. Decidir: una última llamada decide la incidencia con todos los resultados.
"""

from __future__ import annotations

import re
import time
from collections import deque

from curso_core import ClienteLLM, ErrorFormato, Opciones, prompts
from plataforma import ARGUMENTOS, HERRAMIENTAS, Incidencia, Plataforma, Servicio, Severidad
from pydantic import BaseModel, ValidationError

OPCIONES = Opciones(temperatura=0, max_tokens=1200, razonar=False)
MAX_REPLANES = 2
REFERENCIA = re.compile(r"\$\{(\w+)\}")
# El planificador no abre incidencias: eso lo decide el último paso.
HERRAMIENTAS_PLAN = [h for h in HERRAMIENTAS if h.nombre != "abrir_incidencia"]


class Tarea(BaseModel):
    id: str
    herramienta: str
    argumentos: dict
    depende_de: list[str] = []
    para_que: str


class Plan(BaseModel):
    tareas: list[Tarea]


class Decision(BaseModel):
    servicio: Servicio
    abrir: bool
    severidad: Severidad | None = None
    resumen: str
    mitigacion: str


class Ejecucion(BaseModel):
    planes: list[Plan]
    errores_de_plan: list[str]
    resultados: dict[str, str]
    orden: list[str]
    decision: Decision | None
    llamadas_modelo: int
    tokens: int
    segundos: float
    error: str | None = None


def problemas(plan: Plan) -> list[str]:
    """Lo que impide ejecutar el plan. Vacío si es un grafo válido."""
    errores = []
    ids = [t.id for t in plan.tareas]
    if len(set(ids)) != len(ids):
        errores.append("hay ids de tarea repetidos")
    for t in plan.tareas:
        modelo = ARGUMENTOS.get(t.herramienta)
        if modelo is None or t.herramienta == "abrir_incidencia":
            errores.append(f"{t.id}: la herramienta {t.herramienta!r} no está disponible")
            continue
        for dep in t.depende_de:
            if dep not in ids:
                errores.append(f"{t.id}: depende de {dep!r}, que no existe")
        for valor in t.argumentos.values():
            for ref in REFERENCIA.findall(str(valor)):
                if ref not in t.depende_de:
                    errores.append(f"{t.id}: usa ${{{ref}}} sin depender de {ref}")
        # Se validan los argumentos con las referencias sustituidas por un texto cualquiera.
        sustituidos = {
            k: REFERENCIA.sub("x", v) if isinstance(v, str) else v for k, v in t.argumentos.items()
        }
        try:
            modelo.model_validate(sustituidos)
        except ValidationError as e:
            error = e.errors()[0]
            campo = ".".join(str(p) for p in error["loc"]) or "argumentos"
            errores.append(
                f"{t.id}: argumentos de {t.herramienta} no válidos ({campo}): {error['msg']}"
            )
    if not errores and orden_topologico(plan) is None:
        errores.append("las dependencias forman un ciclo")
    return errores


def orden_topologico(plan: Plan) -> list[str] | None:
    """Algoritmo de Kahn: cada tarea va después de todas las que necesita. None si hay ciclo."""
    pendientes = {t.id: set(t.depende_de) for t in plan.tareas}
    listas = deque(i for i, deps in pendientes.items() if not deps)
    orden = []
    while listas:
        actual = listas.popleft()
        orden.append(actual)
        for i, deps in pendientes.items():
            if actual in deps:
                deps.discard(actual)
                if not deps and i not in orden and i not in listas:
                    listas.append(i)
    return orden if len(orden) == len(pendientes) else None


def sustituir(argumentos: dict, resultados: dict[str, str]) -> dict:
    """Pone en cada `${tN}` el resultado de la tarea tN (sus primeras líneas)."""

    def resultado(m: re.Match) -> str:
        return " ".join(resultados[m.group(1)].splitlines()[:3])[:300]

    return {
        k: REFERENCIA.sub(resultado, v) if isinstance(v, str) else v for k, v in argumentos.items()
    }


def describir_herramientas() -> str:
    lineas = []
    for h in HERRAMIENTAS_PLAN:
        args = ", ".join(h.parametros.get("properties", {}))
        lineas.append(f"- {h.nombre}({args}): {h.descripcion}")
    return "\n".join(lineas)


def ejecutar(cliente: ClienteLLM, plataforma: Plataforma, *, rol: str = "agente") -> Ejecucion:
    alerta = plataforma.escenario.alerta
    inicio = time.perf_counter()
    planes, errores_de_plan = [], []
    llamadas = tokens = 0
    error = ""
    plan = None
    try:
        for _ in range(1 + MAX_REPLANES):
            aviso = f"Tu plan anterior no era válido: {error}. Corrígelo." if error else ""
            mensajes = prompts.renderizar(
                prompts.cargar("agentes/planificador"),
                alerta=alerta,
                herramientas=describir_herramientas(),
                error=aviso,
            )
            candidato, r = cliente.extraer(mensajes, Plan, rol=rol, opciones=OPCIONES)
            llamadas, tokens = llamadas + 1, tokens + r.tokens_entrada + r.tokens_salida
            planes.append(candidato)
            fallos = problemas(candidato)
            if not fallos:
                plan = candidato
                break
            error = "; ".join(fallos)
            errores_de_plan.append(error)
        if plan is None:
            return Ejecucion(
                planes=planes,
                errores_de_plan=errores_de_plan,
                resultados={},
                orden=[],
                decision=None,
                llamadas_modelo=llamadas,
                tokens=tokens,
                segundos=time.perf_counter() - inicio,
                error=f"sin plan válido tras {len(planes)} intentos",
            )

        orden = orden_topologico(plan) or []
        por_id = {t.id: t for t in plan.tareas}
        resultados: dict[str, str] = {}
        for i in orden:
            t = por_id[i]
            modelo = ARGUMENTOS[t.herramienta]
            args = modelo.model_validate(sustituir(t.argumentos, resultados))
            resultados[i] = getattr(plataforma, t.herramienta)(args)

        texto = "\n\n".join(
            f"[{i}] {por_id[i].herramienta}({por_id[i].argumentos}) — {por_id[i].para_que}\n"
            f"{resultados[i]}"
            for i in orden
        )
        mensajes = prompts.renderizar(
            prompts.cargar("agentes/plan-decision"), alerta=alerta, resultados=texto
        )
        decision, r = cliente.extraer(mensajes, Decision, rol=rol, opciones=OPCIONES)
        llamadas, tokens = llamadas + 1, tokens + r.tokens_entrada + r.tokens_salida
    except ErrorFormato as e:
        return Ejecucion(
            planes=planes,
            errores_de_plan=errores_de_plan,
            resultados={},
            orden=[],
            decision=None,
            llamadas_modelo=llamadas + 1,
            tokens=tokens,
            segundos=time.perf_counter() - inicio,
            error=str(e)[:200],
        )
    if decision.abrir and decision.severidad is not None:
        plataforma.abrir_incidencia(
            Incidencia(
                servicio=decision.servicio,
                severidad=decision.severidad,
                resumen=decision.resumen,
                mitigacion=decision.mitigacion,
            )
        )
    return Ejecucion(
        planes=planes,
        errores_de_plan=errores_de_plan,
        resultados=resultados,
        orden=orden,
        decision=decision,
        llamadas_modelo=llamadas,
        tokens=tokens,
        segundos=time.perf_counter() - inicio,
    )

"""La plataforma simulada del agente de guardia: escenarios, herramientas y comprobación.

Cada escenario es una alerta más el estado de la plataforma en ese momento (estado de los
servicios, logs, despliegues). Las herramientas leen ese estado; `abrir_incidencia` lo
cambia. Al terminar, `comprobar` mira el estado final, no lo que el agente dice que ha hecho:
si dice que ha abierto la incidencia, la incidencia tiene que existir.

Lo esperado de cada escenario está anclado al corpus del módulo 3: la severidad sale de los
criterios de `severidades.md` y la mitigación, del runbook correspondiente.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03-rag"))

import corpus  # noqa: E402
from curso_core import ClienteLLM, Herramienta, LlamadaHerramienta  # noqa: E402
from curso_core.rag import IndiceVectorial, trocear_por_secciones  # noqa: E402

DATOS = Path(__file__).resolve().parent / "datos"
Servicio = Literal["pagos", "usuarios", "catalogo", "notificaciones", "busqueda"]
Severidad = Literal["critica", "alta", "media", "baja"]


class EstadoServicio(BaseModel):
    estado: Literal["operativo", "degradado", "caido"] = "operativo"
    errores_pct: float = 0.0
    latencia_p95_ms: int = 100
    ultimo_despliegue: str = "hace más de una semana"
    notas: list[str] = []


class Esperado(BaseModel):
    incidencia: bool
    servicio: Servicio | None = None
    severidades: list[Severidad] = []
    # Cada elemento es una lista de alternativas "a|b": la mitigación tiene que contener
    # alguna de cada una.
    mitigacion: list[str] = []
    runbook: str | None = None
    nota: str


class Escenario(BaseModel):
    id: str
    alerta: str
    servicios: dict[Servicio, EstadoServicio] = {}
    logs: dict[Servicio, list[str]] = {}
    esperado: Esperado
    particion: Literal["desarrollo", "prueba"]


def cargar() -> list[Escenario]:
    with (DATOS / "escenarios.jsonl").open(encoding="utf-8") as f:
        return [Escenario.model_validate_json(linea) for linea in f if linea.strip()]


def problemas_de_anclaje(escenarios: list[Escenario], documentos: dict[str, str]) -> list[str]:
    """Lo esperado tiene que salir del corpus: el runbook existe y contiene la mitigación."""
    problemas = []
    for e in escenarios:
        r = e.esperado.runbook
        if r is not None and r not in documentos:
            problemas.append(f"{e.id}: el runbook {r!r} no existe")
            continue
        for clave in e.esperado.mitigacion:
            texto = corpus.normalizar(documentos[r]) if r else ""
            if not any(corpus.normalizar(a) in texto for a in clave.split("|")):
                problemas.append(f"{e.id}: {clave!r} no sale de {r}")
        if e.esperado.incidencia and not (e.esperado.servicio and e.esperado.severidades):
            problemas.append(f"{e.id}: espera incidencia sin servicio o sin severidad")
    return problemas


# --- Herramientas -------------------------------------------------------------------------


class ArgsBuscar(BaseModel):
    consulta: str


class ArgsServicio(BaseModel):
    servicio: Servicio


class ArgsLogs(BaseModel):
    servicio: Servicio
    texto: str = ""


class Incidencia(BaseModel):
    servicio: Servicio
    severidad: Severidad
    resumen: str
    mitigacion: str


# Versión 1: lo mínimo para que funcionen. Es la que se mide primero en la lección 02.
HERRAMIENTAS_V1 = [
    Herramienta.desde(
        "buscar_documentacion",
        "Busca en la documentación interna (runbooks, criterios de severidad, arquitectura, "
        "postmortems) y devuelve los tres fragmentos más relevantes.",
        ArgsBuscar,
    ),
    Herramienta.desde(
        "estado_servicio",
        "Devuelve el estado actual de un servicio: si funciona, su tasa de errores, su "
        "latencia y su último despliegue.",
        ArgsServicio,
    ),
    Herramienta.desde(
        "buscar_logs",
        "Devuelve las líneas recientes de los logs de un servicio que contienen un texto. "
        "Con el texto vacío, devuelve las últimas líneas.",
        ArgsLogs,
    ),
    Herramienta.desde(
        "abrir_incidencia",
        "Abre una incidencia con su servicio, su severidad, un resumen de la causa y la "
        "mitigación propuesta. Solo si hace falta: no todas las alertas lo requieren.",
        Incidencia,
    ),
]


# Versión 2: las mismas herramientas, mejor descritas, tras leer los fallos de la versión 1.
# Los argumentos son los mismos (se validan con los mismos modelos); solo cambia lo que el
# modelo lee sobre ellos.
class ArgsBuscarV2(BaseModel):
    consulta: str = Field(
        description="Qué buscar. Funciona mejor con el síntoma o el error concreto (por "
        "ejemplo, 'too many connections' o 'invalid_grant') que con el nombre de la alerta."
    )


class ArgsLogsV2(BaseModel):
    servicio: Servicio
    texto: str = Field(
        "",
        description="Texto que deben contener las líneas. Déjalo vacío para ver las últimas "
        "líneas: es lo más útil al empezar. Si filtras, usa palabras que aparezcan en los "
        "logs, como ERROR, no el nombre de la alerta.",
    )


class IncidenciaV2(BaseModel):
    servicio: Servicio = Field(description="El servicio afectado.")
    severidad: Severidad = Field(
        description="Según los criterios de severidad: critica, si el servicio está caído "
        "para todos o hay pérdida de dinero o de datos; alta, si una funcionalidad "
        "importante falla para muchos usuarios y no hay alternativa; media, si el fallo es "
        "parcial, intermitente o con alternativa; baja, si es menor, cosmético o una "
        "consulta. Ante la duda entre dos, la más alta."
    )
    resumen: str = Field(description="La causa, en una o dos frases, según logs y estado.")
    mitigacion: str = Field(
        description="La acción concreta que indica el runbook para este caso. Busca el "
        "runbook con buscar_documentacion antes de proponerla."
    )


HERRAMIENTAS = [
    Herramienta.desde(
        "buscar_documentacion",
        "Busca en la documentación interna (runbooks con la mitigación de cada problema, "
        "criterios de severidad, arquitectura, postmortems) y devuelve los tres fragmentos "
        "más relevantes. Consulta el runbook del problema antes de proponer una mitigación.",
        ArgsBuscarV2,
    ),
    HERRAMIENTAS_V1[1],
    Herramienta.desde(
        "buscar_logs",
        "Devuelve las líneas recientes de los logs de un servicio, opcionalmente filtradas "
        "por un texto.",
        ArgsLogsV2,
    ),
    Herramienta.desde(
        "abrir_incidencia",
        "Abre una incidencia. Es la única forma de abrirla: decir en tu respuesta que la "
        "abres no la abre. No la abras si la alerta no requiere acción (por ejemplo, un "
        "pico pasajero ya recuperado o un valor dentro de lo normal).",
        IncidenciaV2,
    ),
]
ARGUMENTOS = {
    "buscar_documentacion": ArgsBuscar,
    "estado_servicio": ArgsServicio,
    "buscar_logs": ArgsLogs,
    "abrir_incidencia": Incidencia,
}


def indice_documentacion(cliente: ClienteLLM) -> IndiceVectorial:
    """El índice denso de la documentación, el del módulo 3. Se construye una vez."""
    indice = IndiceVectorial(cliente)
    indice.añadir([f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)])
    return indice


class Plataforma:
    """El estado de la plataforma durante un escenario, y las herramientas que lo tocan."""

    def __init__(self, escenario: Escenario, indice: IndiceVectorial):
        self.escenario = escenario
        self.indice = indice
        self.incidencias: list[Incidencia] = []
        self.consultados: list[str] = []  # documentos que han salido en las búsquedas

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        """Valida los argumentos y ejecuta la herramienta. Devuelve el resultado y si fue
        válida. Los errores vuelven al modelo como texto, para que pueda corregirse."""
        modelo = ARGUMENTOS.get(llamada.nombre)
        if modelo is None:
            return f"Error: no existe la herramienta {llamada.nombre!r}.", False
        try:
            args = modelo.model_validate(llamada.argumentos)
        except ValidationError as e:
            error = e.errors()[0]
            campo = ".".join(str(p) for p in error["loc"]) or "argumentos"
            return f"Error en los argumentos ({campo}): {error['msg']}", False
        return getattr(self, llamada.nombre)(args), True

    def buscar_documentacion(self, args: ArgsBuscar) -> str:
        resultados = self.indice.buscar(args.consulta, 3)
        self.consultados += [r.fragmento.doc for r in resultados]
        return "\n\n".join(
            f"[{r.fragmento.doc}] {r.fragmento.titulo}\n{r.fragmento.texto}" for r in resultados
        )

    def estado_servicio(self, args: ArgsServicio) -> str:
        e = self.escenario.servicios.get(args.servicio, EstadoServicio())
        lineas = [
            f"servicio: {args.servicio}",
            f"estado: {e.estado}",
            f"errores: {e.errores_pct} %",
            f"latencia p95: {e.latencia_p95_ms} ms",
            f"último despliegue: {e.ultimo_despliegue}",
            *e.notas,
        ]
        return "\n".join(lineas)

    def buscar_logs(self, args: ArgsLogs) -> str:
        lineas = self.escenario.logs.get(args.servicio, ["INFO sin errores en la última hora"])
        texto = corpus.normalizar(args.texto)
        encontradas = [linea for linea in lineas if texto in corpus.normalizar(linea)]
        return "\n".join(encontradas[-10:]) or f"Ninguna línea contiene {args.texto!r}."

    def abrir_incidencia(self, args: Incidencia) -> str:
        self.incidencias.append(args)
        return f"Incidencia INC-{len(self.incidencias)} abierta para {args.servicio}."


# --- Comprobación del estado final --------------------------------------------------------


class Comprobacion(BaseModel):
    ok: bool
    motivo: str
    consulto_runbook: bool


def comprobar(plataforma: Plataforma) -> Comprobacion:
    """¿El estado final es el esperado? Mira las incidencias abiertas, no lo que dijo el agente."""
    e = plataforma.escenario.esperado
    consulto = e.runbook is None or e.runbook in plataforma.consultados
    incidencias = plataforma.incidencias
    if not e.incidencia:
        if incidencias:
            return Comprobacion(
                ok=False,
                motivo="abrió una incidencia que no hacía falta",
                consulto_runbook=consulto,
            )
        return Comprobacion(
            ok=True, motivo="no abrió incidencia, como debía", consulto_runbook=consulto
        )
    if not incidencias:
        return Comprobacion(ok=False, motivo="no abrió la incidencia", consulto_runbook=consulto)
    i = incidencias[0]
    fallos = []
    if i.servicio != e.servicio:
        fallos.append(f"servicio {i.servicio} (esperado {e.servicio})")
    if i.severidad not in e.severidades:
        fallos.append(f"severidad {i.severidad} (esperada {'/'.join(e.severidades)})")
    mitigacion = corpus.normalizar(i.mitigacion + " " + i.resumen)
    for clave in e.mitigacion:
        if not any(corpus.normalizar(a) in mitigacion for a in clave.split("|")):
            fallos.append(f"la mitigación no menciona {clave.split('|')[0]!r}")
    if len(incidencias) > 1:
        fallos.append(f"{len(incidencias)} incidencias abiertas")
    if fallos:
        return Comprobacion(ok=False, motivo="; ".join(fallos), consulto_runbook=consulto)
    return Comprobacion(ok=True, motivo="incidencia correcta", consulto_runbook=consulto)

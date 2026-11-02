"""El asistente de documentación interna, listo para servir (módulo 6).

Es el sistema vigente del módulo 4 (el RAG con reranker que se evaluó) con tres piezas
de producción alrededor:

- Una caché de respuestas: la misma pregunta, con la misma versión del sistema, no vuelve
  a pasar por el modelo. La clave incluye la huella del módulo 4 (prompt, modelos y
  corpus), así que un cambio del sistema invalida la caché sola.
- Un fallback: si el modelo principal falla, responde el siguiente de la lista.
- Una respuesta degradada: si fallan todos, el servicio contesta que ahora no puede, en
  lugar de devolver un error 500 o inventar.

No sabe nada de HTTP: servicio.py lo expone como API.
"""

from __future__ import annotations

import hashlib
import sys
import time
import unicodedata
from pathlib import Path

from opentelemetry import trace
from opentelemetry.trace import StatusCode
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "04-evals"))

import evaluar  # noqa: E402
import guardrails  # noqa: E402
import sistema  # noqa: E402
from curso_core import ClienteLLM, ErrorLLM  # noqa: E402
from curso_core import config as cfg  # noqa: E402

ROLES = ("chat_grande", "chat")  # el del sistema vigente (7B) y, de respaldo, el de 1,5B
tracer = trace.get_tracer("asistente")
DEGRADADA = (
    "Ahora mismo no puedo responder: el servicio de modelos no está disponible. "
    "Inténtalo en unos minutos o consulta directamente la documentación."
)


class Resultado(BaseModel):
    texto: str
    citas: list[int] | None = None
    fuentes: list[str] = []  # los fragmentos recuperados, para comprobar la respuesta
    rol: str | None = None  # quién respondió; None si la respuesta es la degradada
    modelo: str | None = None
    cache: bool = False
    fallback: bool = False  # respondió un modelo que no es el primero de la lista
    errores: list[str] = []  # lo que falló por el camino
    bloqueado: bool = False  # un guardrail sustituyó la respuesta (lección 6.05)
    guardrails: list[str] = []  # qué guardrails actuaron y por qué
    ms: int = 0


def normalizar(pregunta: str) -> str:
    """Minúsculas, sin tildes ni espacios de más: "¿Qué es X?" y "que es x" son la misma."""
    sin_tildes = unicodedata.normalize("NFKD", pregunta).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().strip(" ¿?¡!.").split())


class Cache:
    """Caché en memoria con caducidad. En producción, Redis o similar: compartida entre
    réplicas y que sobreviva a un reinicio."""

    def __init__(self, version: str, ttl_s: float = 3600.0):
        self.version, self.ttl_s = version, ttl_s
        self._datos: dict[str, tuple[float, Resultado]] = {}
        self.aciertos = self.fallos = 0

    def clave(self, pregunta: str) -> str:
        return hashlib.sha256(f"{self.version}|{normalizar(pregunta)}".encode()).hexdigest()

    def leer(self, pregunta: str) -> Resultado | None:
        entrada = self._datos.get(self.clave(pregunta))
        if entrada and time.monotonic() - entrada[0] < self.ttl_s:
            self.aciertos += 1
            return entrada[1]
        self.fallos += 1
        return None

    def guardar(self, pregunta: str, resultado: Resultado) -> None:
        self._datos[self.clave(pregunta)] = (time.monotonic(), resultado)


class Asistente:
    def __init__(
        self,
        roles: tuple[str, ...] = ROLES,
        *,
        cache: bool = True,
        guardrails: bool = False,
        timeout_s: float = 45.0,
        reintentos: int = 0,
        config: cfg.Config | None = None,
    ):
        self.roles = roles
        self.guardrails = guardrails
        config = config or cfg.cargar()
        # Un cliente para buscar (embeddings y reranker) y uno por modelo, cada uno con su
        # límite de tiempo: si el principal se cuelga, hay que soltarlo a tiempo de que
        # responda el siguiente. Sin reintentos: cada reintento de un timeout es otra espera
        # entera (lección 6.01), y para eso está el modelo de respaldo.
        self.indice = sistema.indice(ClienteLLM(config), reranker=evaluar.SISTEMA["reranker"])
        self.clientes = {
            rol: ClienteLLM(config, timeout=timeout_s, reintentos=reintentos) for rol in roles
        }
        self.version = evaluar.huella()
        # La huella cubre los ficheros (prompt, models.toml, corpus, código), no lo que se
        # cambia por entorno (CURSO_ROLES, CURSO_URL_*). Lo que de verdad se usa, aparte
        # (lección 6.07): qué modelo y en qué URL responde cada rol.
        roles_usados = [*roles, "embeddings", "reranker"]
        self.modelos = {}
        for rol in roles_usados:
            _, proveedor, modelo = config.resolver(rol)
            self.modelos[rol] = f"{modelo} @ {proveedor.base_url}"
        self.cache = Cache(self.version) if cache else None

    def responder(self, pregunta: str) -> Resultado:
        # Un span por pregunta (lección 6.02): las llamadas de curso_core cuelgan de él.
        with tracer.start_as_current_span("asistente.responder") as span:
            r = self._con_guardrails(pregunta) if self.guardrails else self._responder(pregunta)
            span.set_attribute("asistente.bloqueado", r.bloqueado)
            span.set_attribute("asistente.cache", r.cache)
            span.set_attribute("asistente.fallback", r.fallback)
            span.set_attribute("asistente.rol", r.rol or "degradada")
            if r.rol is None:
                span.set_status(StatusCode.ERROR, "respuesta degradada")
            return r

    def _con_guardrails(self, pregunta: str) -> Resultado:
        """Revisa la pregunta antes de buscar y la respuesta antes de devolverla."""
        inicio = time.perf_counter()
        entrada = guardrails.revisar_entrada(pregunta)
        if entrada.bloqueado:
            return Resultado(
                texto=guardrails.ABSTENCION,
                bloqueado=True,
                guardrails=entrada.motivos,
                ms=ms_desde(inicio),
            )
        r = self._responder(entrada.texto)
        if r.rol is None:  # la respuesta degradada no viene del modelo: no hay que revisarla
            return r
        salida = guardrails.revisar_salida(r.texto, r.citas, len(r.fuentes))
        return r.model_copy(
            update={
                "texto": salida.texto,
                "bloqueado": salida.bloqueado,
                "guardrails": entrada.motivos + salida.motivos,
                "ms": ms_desde(inicio),
            }
        )

    def _responder(self, pregunta: str) -> Resultado:
        inicio = time.perf_counter()
        if self.cache and (guardado := self.cache.leer(pregunta)):
            return guardado.model_copy(update={"cache": True, "ms": ms_desde(inicio)})
        errores = []
        for i, rol in enumerate(self.roles):
            cliente = self.clientes[rol]
            try:
                r = sistema.responder(
                    cliente,
                    self.indice,
                    pregunta,
                    prompt=evaluar.SISTEMA["prompt"],
                    k=evaluar.SISTEMA["k"],
                    rol=rol,
                )
            except ErrorLLM as e:
                errores.append(f"{rol}: {str(e)[:120]}")
                continue
            resultado = Resultado(
                texto=r.texto,
                citas=r.citas,
                fuentes=[f.id for f in r.recuperados],
                rol=rol,
                modelo=cliente.config.resolver(rol)[2],
                fallback=i > 0,
                errores=errores,
            )
            # Solo se guarda lo que respondió el principal: una respuesta de respaldo
            # (peor) no debe quedarse en la caché cuando el principal vuelva.
            if self.cache and i == 0:
                self.cache.guardar(pregunta, resultado)
            return resultado.model_copy(update={"ms": ms_desde(inicio)})
        return Resultado(texto=DEGRADADA, errores=errores, ms=ms_desde(inicio))


def ms_desde(inicio: float) -> int:
    return round((time.perf_counter() - inicio) * 1000)

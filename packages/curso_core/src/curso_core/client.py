"""Cliente LLM agnóstico al proveedor, con reintentos, tracing y registro de métricas.

Uso mínimo:

    from curso_core import ClienteLLM

    cliente = ClienteLLM()
    respuesta = cliente.chat("¿Qué es un token?")
    print(respuesta.texto, respuesta.tokens_salida, respuesta.latencia_s)

    flujo = cliente.chat_stream("¿Qué es un token?")
    for fragmento in flujo:
        print(fragmento, end="", flush=True)
    print(flujo.respuesta.primer_token_s)

El modelo sale del rol (por defecto, `chat`) en `config/models.toml`.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from collections.abc import Callable, Generator, Iterator
from pathlib import Path
from typing import Literal, NamedTuple

import httpx
from pydantic import BaseModel

from curso_core import config as cfg
from curso_core.tracing import Traza, registrar

# Errores que pueden desaparecer si se reintenta: límite de uso y fallos del servidor.
STATUS_REINTENTABLES = {429, 500, 502, 503, 504}


class Mensaje(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class Opciones(BaseModel):
    """Parámetros de generación, con nombres neutros. `None` deja el valor del servidor."""

    temperatura: float | None = None
    top_p: float | None = None
    semilla: int | None = None
    max_tokens: int | None = None
    # Tamaño de la ventana de contexto. Solo lo admite Ollama; en el resto lo fija el modelo.
    contexto: int | None = None
    # Si se indica, la respuesta incluye la probabilidad de cada token generado y de
    # esta cantidad de alternativas. No todos los proveedores lo admiten.
    alternativas: int | None = None


class Alternativa(BaseModel):
    token: str
    probabilidad: float


class TokenGenerado(BaseModel):
    token: str
    probabilidad: float
    alternativas: list[Alternativa]


class Respuesta(BaseModel):
    texto: str
    proveedor: str
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    latencia_s: float
    coste_usd: float | None
    intentos: int
    id_traza: str
    # Por qué terminó la generación: "stop" (fin natural) o "length" (límite de tokens).
    motivo_fin: str | None = None
    # Solo en streaming: segundos hasta recibir el primer fragmento de texto.
    primer_token_s: float | None = None
    tokens: list[TokenGenerado] | None = None


class ErrorLLM(Exception):
    """Error de una llamada al modelo, con el código HTTP y el cuerpo de la respuesta."""

    def __init__(
        self,
        mensaje: str,
        status: int | None = None,
        cuerpo: str | None = None,
        intentos: int = 1,
    ):
        super().__init__(mensaje)
        self.status = status
        self.cuerpo = cuerpo
        self.intentos = intentos


# --- Dialectos de API --------------------------------------------------------------


class Bruto(NamedTuple):
    """Lo que se extrae de una respuesta completa de cualquier dialecto."""

    texto: str
    tokens_entrada: int
    tokens_salida: int
    # Lista de {token, logprob, top_logprobs: [{token, logprob}]}; mismo formato en ambos.
    logprobs: list[dict] | None
    motivo_fin: str | None


class Trozo(NamedTuple):
    """Lo que se extrae de una línea de una respuesta en streaming."""

    texto: str = ""
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    motivo_fin: str | None = None


def _tokens_generados(logprobs: list[dict] | None) -> list[TokenGenerado] | None:
    if logprobs is None:
        return None
    return [
        TokenGenerado(
            token=lp["token"],
            probabilidad=math.exp(lp["logprob"]),
            alternativas=[
                Alternativa(token=a["token"], probabilidad=math.exp(a["logprob"]))
                for a in lp.get("top_logprobs", [])
            ],
        )
        for lp in logprobs
    ]


def _peticion_ollama(
    modelo: str, mensajes: list[Mensaje], op: Opciones, stream: bool
) -> tuple[str, dict]:
    opciones = {
        "temperature": op.temperatura,
        "top_p": op.top_p,
        "seed": op.semilla,
        "num_predict": op.max_tokens,
        "num_ctx": op.contexto,
    }
    cuerpo = {
        "model": modelo,
        "messages": [m.model_dump() for m in mensajes],
        "stream": stream,
        "options": {k: v for k, v in opciones.items() if v is not None},
    }
    if op.alternativas is not None:
        cuerpo |= {"logprobs": True, "top_logprobs": op.alternativas}
    return "/api/chat", cuerpo


def _respuesta_ollama(datos: dict) -> Bruto:
    return Bruto(
        datos["message"]["content"],
        datos.get("prompt_eval_count", 0),
        datos["eval_count"],
        datos.get("logprobs"),
        datos.get("done_reason"),
    )


def _trozo_ollama(linea: str) -> Trozo:
    """Ollama manda una línea JSON por fragmento; la última (`done`) trae las métricas."""
    datos = json.loads(linea)
    texto = datos.get("message", {}).get("content", "")
    if not datos.get("done"):
        return Trozo(texto)
    return Trozo(
        texto, datos.get("prompt_eval_count", 0), datos["eval_count"], datos.get("done_reason")
    )


def _peticion_openai(
    modelo: str, mensajes: list[Mensaje], op: Opciones, stream: bool
) -> tuple[str, dict]:
    cuerpo = {
        "model": modelo,
        "messages": [m.model_dump() for m in mensajes],
        "temperature": op.temperatura,
        "top_p": op.top_p,
        "seed": op.semilla,
        "max_tokens": op.max_tokens,
    }
    if op.alternativas is not None:
        cuerpo |= {"logprobs": True, "top_logprobs": op.alternativas}
    if stream:
        # Sin include_usage, la API no informa de los tokens en streaming.
        cuerpo |= {"stream": True, "stream_options": {"include_usage": True}}
    return "/chat/completions", {k: v for k, v in cuerpo.items() if v is not None}


def _respuesta_openai(datos: dict) -> Bruto:
    uso = datos["usage"]
    eleccion = datos["choices"][0]
    logprobs = (eleccion.get("logprobs") or {}).get("content")
    return Bruto(
        eleccion["message"]["content"],
        uso["prompt_tokens"],
        uso["completion_tokens"],
        logprobs,
        eleccion.get("finish_reason"),
    )


def _trozo_openai(linea: str) -> Trozo:
    """Server-Sent Events: líneas `data: {json}`, y `data: [DONE]` al final."""
    if not linea.startswith("data:"):
        return Trozo()
    carga = linea.removeprefix("data:").strip()
    if carga == "[DONE]":
        return Trozo()
    datos = json.loads(carga)
    texto, motivo = "", None
    if datos.get("choices"):
        eleccion = datos["choices"][0]
        texto = (eleccion.get("delta") or {}).get("content") or ""
        motivo = eleccion.get("finish_reason")
    uso = datos.get("usage") or {}
    return Trozo(texto, uso.get("prompt_tokens"), uso.get("completion_tokens"), motivo)


class Dialecto(NamedTuple):
    peticion: Callable[[str, list[Mensaje], Opciones, bool], tuple[str, dict]]
    respuesta: Callable[[dict], Bruto]
    trozo: Callable[[str], Trozo]


DIALECTOS = {
    "ollama": Dialecto(_peticion_ollama, _respuesta_ollama, _trozo_ollama),
    "openai": Dialecto(_peticion_openai, _respuesta_openai, _trozo_openai),
}


# --- Cliente -----------------------------------------------------------------------


def espera_backoff(intento: int, base: float = 1.0, maximo: float = 30.0) -> float:
    """Backoff exponencial con jitter: hasta base·2^intento segundos, con tope."""
    return random.uniform(0, min(maximo, base * 2**intento))


def _espera_retry_after(respuesta: httpx.Response) -> float | None:
    valor = respuesta.headers.get("Retry-After")
    try:
        return float(valor) if valor else None
    except ValueError:  # también puede ser una fecha HTTP; en ese caso, backoff normal
        return None


class _Llamada(NamedTuple):
    """Todo lo que hace falta para lanzar y registrar una llamada."""

    proveedor: str
    config: cfg.Proveedor
    modelo: str
    dialecto: Dialecto
    ruta: str
    cuerpo: dict
    traza: dict


class Flujo:
    """Respuesta en streaming: se itera fragmento a fragmento.

    Al terminar la iteración, `respuesta` tiene el texto completo y las métricas.
    """

    def __init__(self, generador: Generator[str, None, Respuesta]):
        self._generador = generador
        self.respuesta: Respuesta | None = None

    def __iter__(self) -> Iterator[str]:
        self.respuesta = yield from self._generador


class ClienteLLM:
    def __init__(
        self,
        config: cfg.Config | None = None,
        *,
        timeout: float = 120.0,
        reintentos: int = 3,
        trazas: Path | None = None,
        transport: httpx.BaseTransport | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ):
        self.config = config or cfg.cargar()
        self.timeout = timeout
        self.reintentos = reintentos
        self.trazas = trazas
        self._transport = transport
        self._dormir = dormir

    def chat(
        self,
        mensajes: str | list[Mensaje],
        *,
        rol: str = "chat",
        opciones: Opciones | None = None,
    ) -> Respuesta:
        llamada = self._preparar(mensajes, rol, opciones, stream=False)
        inicio = time.perf_counter()
        try:
            with self._http(llamada.config) as http:
                r, intentos = self._abrir(http, llamada.ruta, llamada.cuerpo)
                bruto = llamada.dialecto.respuesta(r.json())
        except ErrorLLM as e:
            self._registrar_fallo(llamada, inicio, e)
            raise
        return self._finalizar(llamada, inicio, intentos, bruto)

    def chat_stream(
        self,
        mensajes: str | list[Mensaje],
        *,
        rol: str = "chat",
        opciones: Opciones | None = None,
    ) -> Flujo:
        """Como `chat`, pero devuelve el texto a medida que se genera."""
        llamada = self._preparar(mensajes, rol, opciones, stream=True)
        return Flujo(self._generar(llamada))

    # --- Detalles ------------------------------------------------------------------

    def _preparar(
        self, mensajes: str | list[Mensaje], rol: str, opciones: Opciones | None, stream: bool
    ) -> _Llamada:
        if isinstance(mensajes, str):
            mensajes = [Mensaje(role="user", content=mensajes)]
        nombre, proveedor, modelo = self.config.resolver(rol)
        dialecto = DIALECTOS[proveedor.tipo]
        opciones = opciones or Opciones()
        ruta, cuerpo = dialecto.peticion(modelo, mensajes, opciones, stream)
        traza = dict(
            rol=rol,
            proveedor=nombre,
            modelo=modelo,
            opciones=opciones.model_dump(exclude_none=True),
        )
        return _Llamada(nombre, proveedor, modelo, dialecto, ruta, cuerpo, traza)

    def _generar(self, llamada: _Llamada) -> Generator[str, None, Respuesta]:
        inicio = time.perf_counter()
        partes: list[str] = []
        entrada = salida = 0
        motivo = primer_token = None
        try:
            with self._http(llamada.config) as http:
                r, intentos = self._abrir(http, llamada.ruta, llamada.cuerpo, stream=True)
                try:
                    for linea in r.iter_lines():
                        if not linea.strip():
                            continue
                        trozo = llamada.dialecto.trozo(linea)
                        if trozo.texto:
                            primer_token = primer_token or time.perf_counter() - inicio
                            partes.append(trozo.texto)
                            yield trozo.texto
                        entrada = trozo.tokens_entrada or entrada
                        salida = trozo.tokens_salida or salida
                        motivo = trozo.motivo_fin or motivo
                except httpx.HTTPError as e:
                    # Ya se ha enviado texto al llamante: no se puede reintentar.
                    raise ErrorLLM(f"La conexión se cortó a mitad de respuesta: {e!r}") from e
                finally:
                    r.close()
        except ErrorLLM as e:
            self._registrar_fallo(llamada, inicio, e)
            raise
        bruto = Bruto("".join(partes), entrada, salida, None, motivo)
        return self._finalizar(llamada, inicio, intentos, bruto, primer_token)

    def _http(self, proveedor: cfg.Proveedor) -> httpx.Client:
        cabeceras = {}
        if proveedor.api_key_env:
            clave = os.environ.get(proveedor.api_key_env)
            if not clave:
                raise ErrorLLM(f"Falta la variable de entorno {proveedor.api_key_env} en .env")
            cabeceras["Authorization"] = f"Bearer {clave}"
        return httpx.Client(
            base_url=proveedor.base_url,
            headers=cabeceras,
            timeout=self.timeout,
            transport=self._transport,
        )

    def _abrir(
        self, http: httpx.Client, ruta: str, cuerpo: dict, stream: bool = False
    ) -> tuple[httpx.Response, int]:
        """Envía la petición con reintentos. Devuelve la respuesta y el número de intentos.

        Con `stream=True`, el cuerpo de la respuesta aún no se ha leído: ciérrala al acabar.
        """
        for intento in range(self.reintentos + 1):
            ultimo = intento == self.reintentos
            try:
                r = http.send(http.build_request("POST", ruta, json=cuerpo), stream=stream)
            except httpx.TimeoutException as e:
                if ultimo:
                    raise ErrorLLM(
                        f"Timeout tras {intento + 1} intentos: {e!r}", intentos=intento + 1
                    ) from e
                self._dormir(espera_backoff(intento))
                continue
            except httpx.TransportError as e:
                # Sin conexión no hay nada que reintentar: el servidor no está.
                raise ErrorLLM(f"No se pudo conectar con {http.base_url}: {e!r}") from e

            if r.is_success:
                return r, intento + 1
            r.read()
            r.close()
            if r.status_code in STATUS_REINTENTABLES and not ultimo:
                self._dormir(_espera_retry_after(r) or espera_backoff(intento))
                continue
            raise ErrorLLM(
                f"{r.status_code} {r.reason_phrase} en {r.request.url}: {r.text}",
                status=r.status_code,
                cuerpo=r.text,
                intentos=intento + 1,
            )
        raise AssertionError("inalcanzable")

    def _finalizar(
        self,
        llamada: _Llamada,
        inicio: float,
        intentos: int,
        bruto: Bruto,
        primer_token: float | None = None,
    ) -> Respuesta:
        latencia = time.perf_counter() - inicio
        coste = self._coste(
            llamada.proveedor, llamada.modelo, bruto.tokens_entrada, bruto.tokens_salida
        )
        registro = Traza(
            **llamada.traza,
            ok=True,
            intentos=intentos,
            latencia_s=latencia,
            primer_token_s=primer_token,
            tokens_entrada=bruto.tokens_entrada,
            tokens_salida=bruto.tokens_salida,
            coste_usd=coste,
        )
        registrar(registro, self.trazas)
        return Respuesta(
            texto=bruto.texto,
            proveedor=llamada.proveedor,
            modelo=llamada.modelo,
            tokens_entrada=bruto.tokens_entrada,
            tokens_salida=bruto.tokens_salida,
            latencia_s=latencia,
            coste_usd=coste,
            intentos=intentos,
            id_traza=registro.id,
            motivo_fin=bruto.motivo_fin,
            primer_token_s=primer_token,
            tokens=_tokens_generados(bruto.logprobs),
        )

    def _registrar_fallo(self, llamada: _Llamada, inicio: float, error: ErrorLLM) -> None:
        traza = Traza(
            **llamada.traza,
            ok=False,
            intentos=error.intentos,
            latencia_s=time.perf_counter() - inicio,
            error=str(error),
            status=error.status,
        )
        registrar(traza, self.trazas)

    def _coste(self, proveedor: str, modelo: str, entrada: int, salida: int) -> float | None:
        precio = self.config.precio(proveedor, modelo)
        if precio is None:
            return None
        return (entrada * precio.entrada + salida * precio.salida) / 1_000_000

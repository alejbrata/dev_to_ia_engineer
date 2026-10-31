import json
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import httpx
import pytest
from curso_core import ClienteLLM, ErrorFormato, ErrorLLM, Mensaje, Opciones
from curso_core import config as cfg
from curso_core.tracing import leer
from pydantic import BaseModel

CONFIG = cfg.Config.model_validate(
    {
        "roles": {
            "chat": {"provider": "local", "model": "modelo-local"},
            "remoto": {"provider": "nube", "model": "modelo-nube"},
        },
        "providers": {
            "local": {"tipo": "ollama", "base_url": "http://ollama.test"},
            "nube": {"tipo": "openai", "base_url": "http://nube.test/v1", "api_key_env": "CLAVE"},
        },
        "precios": {"nube/modelo-nube": {"entrada": 1.0, "salida": 2.0}},
    }
)

OLLAMA_OK = {
    "message": {"role": "assistant", "content": "Hola."},
    "prompt_eval_count": 10,
    "eval_count": 4,
}
OPENAI_OK = {
    "choices": [{"message": {"role": "assistant", "content": "Hola."}, "finish_reason": "length"}],
    "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000},
}


def cliente(manejador, tmp_path: Path, esperas: list[float] | None = None, **kw) -> ClienteLLM:
    return ClienteLLM(
        CONFIG,
        trazas=tmp_path / "trazas.jsonl",
        transport=httpx.MockTransport(manejador),
        dormir=(esperas.append if esperas is not None else lambda s: None),
        **kw,
    )


def test_ollama_envia_opciones_y_registra_traza(tmp_path: Path) -> None:
    peticiones = []

    def manejador(request: httpx.Request) -> httpx.Response:
        peticiones.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json=OLLAMA_OK)

    r = cliente(manejador, tmp_path).chat("hola", opciones=Opciones(temperatura=0, semilla=7))

    ruta, cuerpo = peticiones[0]
    assert ruta == "/api/chat"
    assert cuerpo["model"] == "modelo-local"
    assert cuerpo["options"] == {"temperature": 0, "seed": 7}
    assert (r.texto, r.tokens_entrada, r.tokens_salida, r.intentos) == ("Hola.", 10, 4, 1)
    assert r.coste_usd is None  # sin precio configurado
    assert r.motivo_fin is None  # el falso de Ollama no trae done_reason

    [traza] = leer(tmp_path / "trazas.jsonl")
    assert traza.ok and traza.id == r.id_traza and traza.tokens_salida == 4
    assert traza.opciones == {"temperatura": 0, "semilla": 7}


def test_openai_usa_la_clave_y_calcula_el_coste(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAVE", "secreta")
    cabeceras = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cabeceras.append(request.headers["Authorization"])
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json=OPENAI_OK)

    r = cliente(manejador, tmp_path).chat([Mensaje(role="user", content="hola")], rol="remoto")

    assert cabeceras == ["Bearer secreta"]
    assert r.motivo_fin == "length"
    assert r.coste_usd == pytest.approx(1.0 + 1.0)  # 1M de entrada a 1 $ + 0,5M de salida a 2 $


def test_falta_la_clave(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CLAVE", raising=False)
    with pytest.raises(ErrorLLM, match="CLAVE"):
        cliente(lambda r: httpx.Response(200), tmp_path).chat("hola", rol="remoto")


def test_reintenta_429_respetando_retry_after(tmp_path: Path) -> None:
    respuestas = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, json=OLLAMA_OK),
        ]
    )
    esperas: list[float] = []

    r = cliente(lambda req: next(respuestas), tmp_path, esperas).chat("hola")

    assert r.intentos == 2
    assert esperas == [2.0]


def test_401_no_se_reintenta_y_conserva_el_cuerpo(tmp_path: Path) -> None:
    llamadas = []

    def manejador(request: httpx.Request) -> httpx.Response:
        llamadas.append(1)
        return httpx.Response(401, json={"error": "Invalid credentials"})

    with pytest.raises(ErrorLLM) as e:
        cliente(manejador, tmp_path).chat("hola")

    assert e.value.status == 401
    assert "Invalid credentials" in e.value.cuerpo
    assert len(llamadas) == 1
    [traza] = leer(tmp_path / "trazas.jsonl")
    assert not traza.ok and traza.status == 401


def test_500_agota_los_reintentos(tmp_path: Path) -> None:
    esperas: list[float] = []
    with pytest.raises(ErrorLLM) as e:
        cliente(lambda r: httpx.Response(503), tmp_path, esperas, reintentos=2).chat("hola")

    assert e.value.intentos == 3
    assert len(esperas) == 2


def test_timeout_agota_los_reintentos(tmp_path: Path) -> None:
    def manejador(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lento", request=request)

    with pytest.raises(ErrorLLM, match="Timeout tras 2 intentos"):
        cliente(manejador, tmp_path, reintentos=1).chat("hola")


def test_sin_conexion_no_reintenta(tmp_path: Path) -> None:
    def manejador(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("rechazada", request=request)

    with pytest.raises(ErrorLLM, match="No se pudo conectar"):
        cliente(manejador, tmp_path).chat("hola")


def test_alternativas_devuelve_probabilidades(tmp_path: Path) -> None:
    datos = OLLAMA_OK | {
        "logprobs": [
            {
                "token": "Hola",
                "logprob": 0.0,
                "top_logprobs": [
                    {"token": "Hola", "logprob": 0.0},
                    {"token": "Hi", "logprob": -2.0},
                ],
            }
        ]
    }
    cuerpos = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        return httpx.Response(200, json=datos)

    r = cliente(manejador, tmp_path).chat("hola", opciones=Opciones(alternativas=2))

    assert cuerpos[0]["logprobs"] is True and cuerpos[0]["top_logprobs"] == 2
    [token] = r.tokens
    assert token.probabilidad == pytest.approx(1.0)
    assert token.alternativas[1].token == "Hi"
    assert token.alternativas[1].probabilidad == pytest.approx(0.1353, abs=1e-4)


def test_sin_alternativas_no_pide_probabilidades(tmp_path: Path) -> None:
    def manejador(request: httpx.Request) -> httpx.Response:
        assert "logprobs" not in json.loads(request.content)
        return httpx.Response(200, json=OLLAMA_OK)

    assert cliente(manejador, tmp_path).chat("hola").tokens is None


def test_stream_ollama_entrega_fragmentos_y_metricas(tmp_path: Path) -> None:
    lineas = [
        {"message": {"content": "Ho"}, "done": False},
        {"message": {"content": "la."}, "done": False},
        {
            "message": {"content": ""},
            "done": True,
            "prompt_eval_count": 9,
            "eval_count": 2,
            "done_reason": "stop",
        },
    ]
    cuerpo = "\n".join(json.dumps(linea) for linea in lineas) + "\n"

    def manejador(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, text=cuerpo)

    flujo = cliente(manejador, tmp_path).chat_stream("hola")
    assert list(flujo) == ["Ho", "la."]
    r = flujo.respuesta
    assert (r.texto, r.tokens_entrada, r.tokens_salida, r.motivo_fin) == ("Hola.", 9, 2, "stop")
    assert r.primer_token_s is not None and r.primer_token_s <= r.latencia_s
    [traza] = leer(tmp_path / "trazas.jsonl")
    assert traza.primer_token_s == r.primer_token_s


def test_stream_openai_lee_server_sent_events(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAVE", "secreta")
    eventos = [
        {"choices": [{"delta": {"content": "Ho"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "la."}, "finish_reason": "stop"}]},
        {"choices": [], "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0}},
    ]
    cuerpo = "".join(f"data: {json.dumps(e)}\n\n" for e in eventos) + "data: [DONE]\n\n"

    def manejador(request: httpx.Request) -> httpx.Response:
        enviado = json.loads(request.content)
        assert enviado["stream"] is True and enviado["stream_options"] == {"include_usage": True}
        return httpx.Response(200, text=cuerpo)

    flujo = cliente(manejador, tmp_path).chat_stream("hola", rol="remoto")
    assert "".join(flujo) == "Hola."
    assert flujo.respuesta.motivo_fin == "stop"
    assert flujo.respuesta.coste_usd == pytest.approx(1.0)


def test_stream_con_error_http_no_entrega_texto(tmp_path: Path) -> None:
    flujo = cliente(lambda r: httpx.Response(401, text="no"), tmp_path).chat_stream("hola")
    with pytest.raises(ErrorLLM) as e:
        list(flujo)
    assert e.value.status == 401
    assert flujo.respuesta is None


def test_reutiliza_la_conexion_del_proveedor(tmp_path: Path) -> None:
    c = cliente(lambda r: httpx.Response(200, json=OLLAMA_OK), tmp_path)
    c.chat("uno")
    c.chat("dos")
    assert len(c._clientes) == 1
    c.cerrar()
    assert c._clientes == {}


class Clasificacion(BaseModel):
    categoria: Literal["red", "otro"]


def test_extraer_manda_el_esquema_y_valida(tmp_path: Path) -> None:
    cuerpos = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        return httpx.Response(
            200, json=OLLAMA_OK | {"message": {"content": '{"categoria": "red"}'}}
        )

    objeto, r = cliente(manejador, tmp_path).extraer("hola", Clasificacion)
    assert objeto == Clasificacion(categoria="red")
    assert cuerpos[0]["format"]["properties"]["categoria"]["enum"] == ["red", "otro"]
    assert r.tokens_salida == 4


def test_extraer_openai_usa_response_format(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAVE", "x")
    cuerpos = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        datos = OPENAI_OK | {
            "choices": [{"message": {"content": '{"categoria": "otro"}'}, "finish_reason": "stop"}]
        }
        return httpx.Response(200, json=datos)

    objeto, _ = cliente(manejador, tmp_path).extraer("hola", Clasificacion, rol="remoto")
    assert objeto.categoria == "otro"
    assert cuerpos[0]["response_format"]["type"] == "json_schema"


@pytest.mark.parametrize("texto", ['{"categoria": "hardware"}', '{"categoria": "re'])
def test_extraer_lanza_error_formato(tmp_path: Path, texto: str) -> None:
    respuesta = OLLAMA_OK | {"message": {"content": texto}}
    with pytest.raises(ErrorFormato) as e:
        cliente(lambda r: httpx.Response(200, json=respuesta), tmp_path).extraer(
            "hola", Clasificacion
        )
    assert e.value.texto == texto


def test_el_proveedor_puede_renombrar_el_limite_de_tokens() -> None:
    """OpenAI pide `max_completion_tokens`; el resto de servidores, `max_tokens`."""
    datos = CONFIG.model_dump()
    datos["providers"]["nube"]["parametro_max_tokens"] = "max_completion_tokens"
    c = ClienteLLM(cfg.Config.model_validate(datos))
    llamada = c._preparar("Hola", "remoto", Opciones(max_tokens=50), stream=False)
    assert llamada.cuerpo["max_completion_tokens"] == 50 and "max_tokens" not in llamada.cuerpo
    por_defecto = ClienteLLM(CONFIG)._preparar("Hola", "remoto", Opciones(max_tokens=50), False)
    assert por_defecto.cuerpo["max_tokens"] == 50


def test_el_proveedor_puede_omitir_parametros_que_rechaza() -> None:
    datos = CONFIG.model_dump()
    datos["providers"]["nube"]["omitir"] = ["temperature"]
    c = ClienteLLM(cfg.Config.model_validate(datos))
    llamada = c._preparar("Hola", "remoto", Opciones(temperatura=0), stream=False)
    assert "temperature" not in llamada.cuerpo


def test_esquema_estricto_cierra_todos_los_objetos() -> None:
    from curso_core.client import esquema_estricto

    class Cita(BaseModel):
        texto: str

    class ConCitas(BaseModel):
        respuesta: str
        citas: list[Cita] = []

    estricto = esquema_estricto(ConCitas.model_json_schema())
    assert estricto["additionalProperties"] is False
    assert estricto["required"] == ["respuesta", "citas"]
    assert estricto["$defs"]["Cita"]["additionalProperties"] is False
    assert "additionalProperties" not in ConCitas.model_json_schema()  # no toca el original


# --- Claude (SDK oficial), con un SDK falso: sin red ni clave -----------------------------

CONFIG_CLAUDE = cfg.Config.model_validate(
    {
        "roles": {
            "claude": {"provider": "anthropic", "model": "claude-opus-5-5"},
            "claude_otro": {"provider": "anthropic", "model": "modelo-sin-reserva"},
        },
        "providers": {
            "anthropic": {
                "tipo": "anthropic",
                "base_url": "https://api.anthropic.com",
                "api_key_env": "CLAVE_CLAUDE",
            }
        },
        "precios": {"anthropic/claude-opus-5-5": {"entrada": 4.0, "salida": 20.0}},
    }
)


def mensaje_claude(texto: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=texto)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000),
    )


class FlujoFalso:
    def __init__(self, partes: list[str]):
        self.text_stream = iter(partes)
        self._final = mensaje_claude("".join(partes))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get_final_message(self):
        return self._final


class APIFalsa:
    def __init__(self):
        self.peticiones: list[dict] = []

    def create(self, **kwargs):
        self.peticiones.append(kwargs)
        return mensaje_claude('{"respuesta": "Hola", "citas": [1]}')

    def stream(self, **kwargs):
        self.peticiones.append(kwargs)
        return FlujoFalso(["Ho", "la"])


def cliente_claude(tmp_path: Path) -> tuple[ClienteLLM, APIFalsa]:
    c = ClienteLLM(CONFIG_CLAUDE, trazas=tmp_path / "trazas.jsonl")
    api = APIFalsa()
    c._sdk_claude["anthropic"] = SimpleNamespace(messages=api, beta=SimpleNamespace(messages=api))
    return c, api


def test_peticion_claude_sin_muestreo_y_con_sistema_aparte(tmp_path: Path) -> None:
    c, api = cliente_claude(tmp_path)
    mensajes = [Mensaje(role="system", content="Sé breve."), Mensaje(role="user", content="Hola")]
    c.chat(mensajes, rol="claude", opciones=Opciones(temperatura=0, max_tokens=50))
    peticion = api.peticiones[0]
    assert peticion["system"] == "Sé breve."
    assert peticion["messages"] == [{"role": "user", "content": "Hola"}]
    assert peticion["max_tokens"] == 50 and "temperature" not in peticion
    # Opus 5.5 admite la reserva del servidor ante un rechazo; otros modelos, no.
    assert peticion["fallbacks"] == "default"
    c.chat("Hola", rol="claude_otro")
    assert "fallbacks" not in api.peticiones[1] and api.peticiones[1]["max_tokens"] == 16000


def test_claude_extrae_con_esquema_estricto_y_registra_coste(tmp_path: Path) -> None:
    class ConCitas(BaseModel):
        respuesta: str
        citas: list[int]

    c, api = cliente_claude(tmp_path)
    objeto, r = c.extraer("Hola", ConCitas, rol="claude")
    assert objeto.citas == [1] and r.motivo_fin == "stop"
    esquema = api.peticiones[0]["output_config"]["format"]["schema"]
    assert esquema["additionalProperties"] is False
    assert r.coste_usd == pytest.approx(4.0 + 2.0)  # 1M de entrada a 4 $ y 100k de salida a 20 $
    assert leer(tmp_path / "trazas.jsonl")[0].proveedor == "anthropic"


def test_claude_en_streaming(tmp_path: Path) -> None:
    c, _ = cliente_claude(tmp_path)
    flujo = c.chat_stream("Hola", rol="claude")
    assert list(flujo) == ["Ho", "la"]
    assert flujo.respuesta.texto == "Hola" and flujo.respuesta.primer_token_s is not None


def test_claude_sin_clave(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CLAVE_CLAUDE", raising=False)
    c = ClienteLLM(CONFIG_CLAUDE, trazas=tmp_path / "trazas.jsonl")
    with pytest.raises(ErrorLLM, match="Falta la variable de entorno CLAVE_CLAUDE"):
        c.chat("Hola", rol="claude")
    assert leer(tmp_path / "trazas.jsonl")[0].ok is False

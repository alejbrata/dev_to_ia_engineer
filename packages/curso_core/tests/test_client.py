import json
from pathlib import Path

import httpx
import pytest
from curso_core import ClienteLLM, ErrorLLM, Mensaje, Opciones
from curso_core import config as cfg
from curso_core.tracing import leer

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
    "choices": [{"message": {"role": "assistant", "content": "Hola."}}],
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

    [traza] = leer(tmp_path / "trazas.jsonl")
    assert traza.ok and traza.id == r.id_traza and traza.tokens_salida == 4


def test_openai_usa_la_clave_y_calcula_el_coste(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAVE", "secreta")
    cabeceras = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cabeceras.append(request.headers["Authorization"])
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json=OPENAI_OK)

    r = cliente(manejador, tmp_path).chat([Mensaje(role="user", content="hola")], rol="remoto")

    assert cabeceras == ["Bearer secreta"]
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

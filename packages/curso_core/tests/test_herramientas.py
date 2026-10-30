import json
from pathlib import Path

import httpx
import pytest
from curso_core import ClienteLLM, Herramienta, LlamadaHerramienta, Mensaje, Opciones
from curso_core import config as cfg
from pydantic import BaseModel

CONFIG = cfg.Config.model_validate(
    {
        "roles": {
            "chat": {"provider": "local", "model": "m"},
            "remoto": {"provider": "nube", "model": "m"},
        },
        "providers": {
            "local": {"tipo": "ollama", "base_url": "http://ollama.test"},
            "nube": {"tipo": "openai", "base_url": "http://nube.test/v1"},
        },
    }
)


class ArgsEstado(BaseModel):
    servicio: str


ESTADO = Herramienta.desde("estado_servicio", "Estado de un servicio.", ArgsEstado)


def cliente(manejador, tmp_path: Path) -> ClienteLLM:
    return ClienteLLM(CONFIG, trazas=tmp_path / "t.jsonl", transport=httpx.MockTransport(manejador))


def test_herramienta_desde_un_modelo() -> None:
    assert ESTADO.parametros["properties"]["servicio"]["type"] == "string"


def test_ollama_manda_herramientas_y_lee_llamadas(tmp_path: Path) -> None:
    cuerpos = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        mensaje = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "estado_servicio", "arguments": {"servicio": "pagos"}}}
            ],
        }
        return httpx.Response(200, json={"message": mensaje, "eval_count": 5})

    r = cliente(manejador, tmp_path).chat("¿Va pagos?", opciones=Opciones(herramientas=[ESTADO]))

    herramienta = cuerpos[0]["tools"][0]
    assert herramienta["type"] == "function"
    assert herramienta["function"]["name"] == "estado_servicio"
    assert r.llamadas == [
        LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "pagos"})
    ]


def test_ollama_devuelve_el_resultado_de_la_herramienta(tmp_path: Path) -> None:
    cuerpos = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}, "eval_count": 1})

    llamada = LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "pagos"})
    mensajes = [
        Mensaje(role="user", content="¿Va pagos?"),
        Mensaje(role="assistant", llamadas=[llamada]),
        Mensaje(role="tool", content="caído", respuesta_a=llamada),
    ]
    cliente(manejador, tmp_path).chat(mensajes)

    _, asistente, herramienta = cuerpos[0]["messages"]
    assert asistente["tool_calls"][0]["function"]["arguments"] == {"servicio": "pagos"}
    assert herramienta == {"role": "tool", "content": "caído", "tool_name": "estado_servicio"}


def test_openai_lee_argumentos_en_texto_y_conserva_el_id(tmp_path: Path) -> None:
    llamadas = [
        {
            "id": "c1",
            "type": "function",
            "function": {"name": "estado_servicio", "arguments": '{"servicio": "pagos"}'},
        },
        {
            "id": "c2",
            "type": "function",
            "function": {"name": "estado_servicio", "arguments": '{"servicio": '},
        },
    ]
    datos = {
        "choices": [
            {"message": {"content": None, "tool_calls": llamadas}, "finish_reason": "tool_calls"}
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    r = cliente(lambda req: httpx.Response(200, json=datos), tmp_path).chat("x", rol="remoto")

    assert r.texto == ""
    assert r.llamadas[0] == LlamadaHerramienta(
        id="c1", nombre="estado_servicio", argumentos={"servicio": "pagos"}
    )
    assert r.llamadas[1].argumentos == {"_sin_interpretar": '{"servicio": '}
    assert r.como_mensaje().llamadas == r.llamadas


def test_openai_devuelve_el_resultado_con_su_id(tmp_path: Path) -> None:
    cuerpos = []

    def manejador(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        datos = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        return httpx.Response(200, json=datos)

    llamada = LlamadaHerramienta(id="c1", nombre="estado_servicio", argumentos={"servicio": "x"})
    cliente(manejador, tmp_path).chat(
        [
            Mensaje(role="assistant", llamadas=[llamada]),
            Mensaje(role="tool", content="ok", respuesta_a=llamada),
        ],
        rol="remoto",
    )
    asistente, herramienta = cuerpos[0]["messages"]
    assert asistente["tool_calls"][0]["function"]["arguments"] == '{"servicio": "x"}'
    assert herramienta["tool_call_id"] == "c1"


def test_embeber_ollama_y_openai(tmp_path: Path) -> None:
    def ollama(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        return httpx.Response(
            200, json={"embeddings": [[1.0, 0.0], [0.0, 1.0]], "prompt_eval_count": 4}
        )

    def openai(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        datos = [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]
        return httpx.Response(200, json={"data": datos, "usage": {"prompt_tokens": 4}})

    e = cliente(ollama, tmp_path).embeber(["a", "b"], rol="chat")
    assert e.vectores == [[1.0, 0.0], [0.0, 1.0]] and e.tokens_entrada == 4
    e = cliente(openai, tmp_path).embeber(["a", "b"], rol="remoto")
    assert e.vectores == [[1.0, 0.0], [0.0, 1.0]]  # ordenados por index


def test_reordenar_devuelve_puntuaciones_en_orden_de_entrada(tmp_path: Path) -> None:
    def rerank(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/rerank"
        assert json.loads(request.content)["documents"] == ["a", "b", "c"]
        resultados = [
            {"index": 2, "relevance_score": 3.0},
            {"index": 0, "relevance_score": 1.0},
            {"index": 1, "relevance_score": -2.0},
        ]
        return httpx.Response(200, json={"results": resultados, "usage": {"prompt_tokens": 9}})

    r = cliente(rerank, tmp_path).reordenar("q", ["a", "b", "c"], rol="remoto")
    assert r.puntuaciones == [1.0, -2.0, 3.0] and r.tokens_entrada == 9


def test_reordenar_rechaza_ollama(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="/rerank"):
        cliente(lambda r: httpx.Response(200), tmp_path).reordenar("q", ["a"], rol="chat")

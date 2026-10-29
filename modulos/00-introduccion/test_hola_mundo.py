import json
from pathlib import Path

import hola_mundo as hm
import httpx
import pytest

RESPUESTA = {
    "model": "modelo-de-prueba",
    "message": {"role": "assistant", "content": "Hola."},
    "done": True,
    "prompt_eval_count": 12,
    "eval_count": 3,
    "load_duration": 500_000_000,
    "total_duration": 900_000_000,
}


def cliente_falso(manejador) -> httpx.Client:
    return httpx.Client(base_url="http://ollama.test", transport=httpx.MockTransport(manejador))


def test_preguntar_envia_el_modelo_y_la_pregunta() -> None:
    peticiones: list[dict] = []

    def manejador(request: httpx.Request) -> httpx.Response:
        peticiones.append(json.loads(request.content))
        return httpx.Response(200, json=RESPUESTA)

    respuesta, latencia = hm.preguntar(cliente_falso(manejador), "modelo-de-prueba", "hola")

    assert peticiones == [
        {
            "model": "modelo-de-prueba",
            "messages": [{"role": "user", "content": "hola"}],
            "stream": False,
        }
    ]
    assert respuesta.message.content == "Hola."
    assert (respuesta.prompt_eval_count, respuesta.eval_count) == (12, 3)
    assert latencia >= 0


def test_preguntar_propaga_los_errores_http() -> None:
    def manejador(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'x' not found"})

    with pytest.raises(httpx.HTTPStatusError):
        hm.preguntar(cliente_falso(manejador), "x", "hola")


def test_leer_config_resuelve_el_proveedor_del_rol_chat(tmp_path: Path) -> None:
    ruta = tmp_path / "models.toml"
    ruta.write_text(
        '[roles.chat]\nprovider = "local"\nmodel = "m"\n\n'
        '[providers.local]\nbase_url = "http://localhost:1234"\n',
        encoding="utf-8",
    )
    assert hm.leer_config(ruta) == hm.Config(base_url="http://localhost:1234", modelo="m")


def test_config_del_repo_tiene_rol_chat() -> None:
    config = hm.leer_config(hm.RAIZ / "config" / "models.toml")
    assert config.base_url and config.modelo

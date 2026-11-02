"""El asistente de producción sin modelos: la caché y la API con un asistente falso."""

from __future__ import annotations

import asistente
from asistente import Cache, Resultado, normalizar


def test_normalizar_iguala_mayusculas_tildes_y_signos():
    assert normalizar("¿Cada cuánto caduca el token?") == normalizar("cada cuanto caduca el TOKEN")


def test_la_cache_depende_de_la_version_y_caduca(monkeypatch):
    reloj = [0.0]
    monkeypatch.setattr(asistente.time, "monotonic", lambda: reloj[0])
    v1 = Cache("v1", ttl_s=10)
    v1.guardar("¿Qué es X?", Resultado(texto="X es..."))
    assert v1.leer("que es x").texto == "X es..."
    assert Cache("v2").leer("que es x") is None  # otra versión del sistema, otra clave
    reloj[0] = 11
    assert v1.leer("que es x") is None  # caducada
    assert (v1.aciertos, v1.fallos) == (1, 1)


def test_la_api_valida_y_responde(monkeypatch):
    import servicio
    from fastapi.testclient import TestClient

    class Falso:
        version, roles, cache = "v", ("a",), None

        def responder(self, pregunta: str) -> Resultado:
            return Resultado(texto=f"eco: {pregunta}", rol="a")

    monkeypatch.setattr(servicio, "Asistente", lambda **_: Falso())
    with TestClient(servicio.app) as cliente:
        assert cliente.post("/preguntas", json={"pregunta": "hola"}).json()["texto"] == "eco: hola"
        assert cliente.post("/preguntas", json={"pregunta": ""}).status_code == 422
        trabajo = cliente.post("/trabajos", json={"pregunta": "lote"})
        assert trabajo.status_code == 202
        assert cliente.get("/trabajos/no-existe").status_code == 404
        assert cliente.get("/salud").json()["estado"] == "ok"
        metricas = cliente.get("/metrics").text
        assert 'asistente_preguntas_total{resultado="principal"}' in metricas


def test_privacidad_detecta_formas_y_valida_el_dni():
    import privacidad

    texto = "Soy Ana (ana@gmail.com, 612 345 678), DNI 12345678Z; versión 3.7.2"
    assert {t for t, _ in privacidad.encontrar(texto)} == {"EMAIL", "TELEFONO", "DNI"}
    assert privacidad.encontrar("El documento 12345678A no es válido") == []  # letra mala
    assert "[EMAIL]" in privacidad.redactar(texto) and "ana@" not in privacidad.redactar(texto)
    assert privacidad.buscar_secretos('KEY = "sk-curso-0123456789abcdefghij"')
    assert not privacidad.buscar_secretos("normal = 1")

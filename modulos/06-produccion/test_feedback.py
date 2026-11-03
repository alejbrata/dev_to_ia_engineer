"""Lección 6.10 sin modelos: el registro de respuestas, la cola de revisión y el endpoint."""

from __future__ import annotations

import json

import feedback
import servicio
from asistente import Resultado
from fastapi.testclient import TestClient


def _resultado(texto: str = "200") -> Resultado:
    return Resultado(texto=texto, fuentes=["pagos#1"], rol="chat_grande")


def test_una_valoracion_se_une_con_su_respuesta(tmp_path) -> None:
    registro = feedback.Registro(ruta=tmp_path / "valoraciones.jsonl")
    registro.guardar("a1", "¿Límite del pool?", _resultado(), "7b")
    fila = registro.valorar(feedback.Valoracion(id="a1", util=False, comentario="no es eso"))
    assert fila["pregunta"] == "¿Límite del pool?" and fila["version"] == "7b"
    guardada = json.loads((tmp_path / "valoraciones.jsonl").read_text(encoding="utf-8"))
    assert guardada["util"] is False and guardada["respuesta"] == "200"
    assert registro.valorar(feedback.Valoracion(id="no-existe", util=True)) is None


def test_el_registro_olvida_las_respuestas_mas_antiguas() -> None:
    registro = feedback.Registro(maximo=2)
    for i in range(3):
        registro.guardar(f"r{i}", "p", _resultado(), "7b")
    assert registro.valorar(feedback.Valoracion(id="r0", util=True)) is None
    assert registro.valorar(feedback.Valoracion(id="r2", util=True)) is not None


def test_la_cola_agrupa_los_no_por_pregunta_y_version() -> None:
    def v(pregunta, version, util=False):
        return {"pregunta": pregunta, "version": version, "respuesta": "x", "fuentes": [],
                "util": util}  # fmt: skip

    valoraciones = [
        v("¿Qué es X?", "7b"),
        v("que es x", "7b"),  # la misma pregunta, normalizada
        v("¿Qué es X?", "1.5b"),
        v("¿Y Z?", "7b"),
        v("¿Y Z?", "7b", util=True),  # un 👍 no entra en la cola
    ]
    cola = feedback.cola_de_revision(valoraciones, en_la_eval={"y z"})
    assert [(g["version"], g["votos"], g["en_la_eval"]) for g in cola] == [
        ("7b", 2, False),
        ("1.5b", 1, False),
        ("7b", 1, True),
    ]


def test_el_endpoint_registra_y_rechaza_ids_desconocidos() -> None:
    servicio.estado["registro"] = feedback.Registro()
    servicio.estado["registro"].guardar("a1", "p", _resultado(), "7b")
    cliente = TestClient(servicio.app)  # sin `with`: no arranca el asistente ni los modelos
    assert cliente.post("/valoraciones", json={"id": "a1", "util": True}).status_code == 201
    assert cliente.post("/valoraciones", json={"id": "zz", "util": True}).status_code == 404
    assert cliente.post("/valoraciones", json={"id": "a1"}).status_code == 422

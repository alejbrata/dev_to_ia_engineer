"""El reto del módulo 2, sin modelos: los criterios, y lo que acepta cada esquema."""

from pathlib import Path

import pytest
from curso_core.retos import cargar
from pydantic import ValidationError

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")
partida = cargar(RETO / "extractor.py")
solucion = cargar(RETO / "solucion" / "extractor.py")


def test_avisos_perfectos_superan_el_reto() -> None:
    correos = solucion.correos()
    avisos = [solucion.Aviso(motivo="-", **c["esperado"]) for c in correos]
    assert all(c.ok for c in comprobar.criterios(solucion, avisos, correos))


def test_sin_avisos_no_se_supera() -> None:
    correos = partida.correos()
    assert not any(c.ok for c in comprobar.criterios(partida, [None] * len(correos), correos))


def test_el_esquema_de_partida_acepta_horas_que_no_lo_son() -> None:
    datos = {"servicio": "catalogo", "severidad": "alta", "afecta_clientes": False}
    assert partida.Aviso(**datos, hora_inicio="lunes").hora_inicio == "lunes"
    with pytest.raises(ValidationError):
        solucion.Aviso(motivo="-", **datos, hora_inicio="lunes")
    with pytest.raises(ValidationError):
        solucion.Aviso(motivo="-", **datos, hora_inicio="6:00")
    assert solucion.Aviso(motivo="-", **datos, hora_inicio=None).hora_inicio is None


def test_la_solucion_usa_otro_rol_que_la_partida() -> None:
    assert (partida.ROL, solucion.ROL) == ("chat", "chat_grande")


def test_desarrollo_y_prueba_no_se_mezclan() -> None:
    desarrollo, prueba = partida.correos("desarrollo"), partida.correos("prueba")
    assert (len(desarrollo), len(prueba)) == (15, 10)
    assert not {c["texto"] for c in desarrollo} & {c["texto"] for c in prueba}
    # Con avisos perfectos también se supera la prueba.
    avisos = [solucion.Aviso(motivo="-", **c["esperado"]) for c in prueba]
    assert all(c.ok for c in comprobar.criterios(solucion, avisos, prueba, "prueba"))

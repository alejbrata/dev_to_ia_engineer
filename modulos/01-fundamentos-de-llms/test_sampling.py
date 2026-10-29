import pytest
import sampling

DISTRIBUCION = {"bl": 0.5, "az": 0.3, "amar": 0.2}


def test_temperatura_uno_conserva_las_proporciones() -> None:
    reescalada = sampling.reescalar(DISTRIBUCION, 1.0)
    assert reescalada == pytest.approx(DISTRIBUCION)


def test_temperatura_baja_concentra_y_alta_aplana() -> None:
    baja = sampling.reescalar(DISTRIBUCION, 0.3)
    alta = sampling.reescalar(DISTRIBUCION, 2.0)
    assert baja["bl"] > DISTRIBUCION["bl"] > alta["bl"]
    assert alta["amar"] > DISTRIBUCION["amar"] > baja["amar"]
    assert sum(alta.values()) == pytest.approx(1.0)


def test_temperatura_cero_es_el_mas_probable() -> None:
    assert sampling.reescalar(DISTRIBUCION, 0) == {"bl": 1.0, "az": 0.0, "amar": 0.0}


def test_barra() -> None:
    assert sampling.barra(0.5, ancho=10) == "#####"

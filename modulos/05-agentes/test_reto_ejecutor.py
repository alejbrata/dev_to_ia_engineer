"""El reto del módulo 5: el código de partida falla los criterios y la solución los cumple.
Es determinista (API simulada y reloj falso), así que se comprueba entero en CI."""

from pathlib import Path

from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")


def test_el_codigo_de_partida_no_cumple_ningun_criterio() -> None:
    assert not any(c.ok for c in comprobar.comprobar(cargar(RETO / "ejecutor.py")))


def test_la_solucion_supera_el_reto() -> None:
    assert all(c.ok for c in comprobar.comprobar(cargar(RETO / "solucion" / "ejecutor.py")))

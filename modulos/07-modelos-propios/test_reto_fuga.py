"""El reto del módulo 7: la partida no supera el reto y la solución sí. Sin modelos."""

from pathlib import Path

from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")


def test_el_codigo_de_partida_no_supera_el_reto() -> None:
    criterios = comprobar.comprobar(cargar(RETO / "fuga.py"))
    assert [c.ok for c in criterios] == [False, False, True, False, False, False]


def test_la_solucion_supera_el_reto() -> None:
    assert all(c.ok for c in comprobar.comprobar(cargar(RETO / "solucion" / "fuga.py")))

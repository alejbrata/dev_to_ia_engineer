"""El reto del módulo 1: el código de partida falla los criterios y la solución los cumple."""

import json
from pathlib import Path

from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")


def test_el_log_es_el_que_genera_el_script() -> None:
    grabado = [json.loads(x) for x in (RETO / "llamadas.jsonl").read_text().splitlines()]
    assert grabado == cargar(RETO / "generar_log.py").llamadas()


def test_el_codigo_de_partida_no_supera_el_reto() -> None:
    criterios = comprobar.comprobar(cargar(RETO / "factura.py"))
    assert [c.ok for c in criterios] == [False, False, True, False, False, False, False]


def test_la_solucion_supera_el_reto() -> None:
    assert all(c.ok for c in comprobar.comprobar(cargar(RETO / "solucion" / "factura.py")))

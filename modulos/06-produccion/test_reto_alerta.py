"""El reto del módulo 6: el log es el que genera el script, la partida no supera el reto y la
solución sí. No usa modelos: se comprueba entero en CI."""

import json
from pathlib import Path

from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")


def test_el_log_es_el_que_genera_el_script() -> None:
    grabado = [json.loads(x) for x in (RETO / "peticiones.jsonl").read_text().splitlines()]
    assert grabado == cargar(RETO / "generar_peticiones.py").peticiones()


def test_el_codigo_de_partida_no_supera_el_reto() -> None:
    criterios = comprobar.comprobar(cargar(RETO / "alerta.py"))
    assert [c.ok for c in criterios] == [False, False, True, False, False]


def test_la_solucion_supera_el_reto() -> None:
    assert all(c.ok for c in comprobar.comprobar(cargar(RETO / "solucion" / "alerta.py")))

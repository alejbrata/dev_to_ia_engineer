"""El reto del módulo 0: el código de partida falla los criterios y la solución los cumple."""

from pathlib import Path

from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")


def test_el_codigo_de_partida_no_supera_el_reto() -> None:
    criterios = comprobar.comprobar(cargar(RETO / "diagnostico.py"))
    assert [c.nombre for c in criterios if not c.ok] == [
        "con Ollama parado, dice que no responde (sin romperse)",
        "un modelo sin etiqueta está descargado si Ollama lo lista como :latest",
        ".env en .gitignore, pero ya en git: está versionado",
    ]


def test_la_solucion_supera_el_reto() -> None:
    assert all(c.ok for c in comprobar.comprobar(cargar(RETO / "solucion" / "diagnostico.py")))

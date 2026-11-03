"""El reto del módulo 4, sin modelos: los casos, los criterios y el veredicto del juez."""

from pathlib import Path

from curso_core.evals import Acuerdo
from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")
partida = cargar(RETO / "juez.py")
solucion = cargar(RETO / "solucion" / "juez.py")


class _JuezFijo:
    """Devuelve unos pasos del procedimiento y la revisión que se le pida, sin modelo."""

    def __init__(self, pasos: list[str], incluidos: list[bool]):
        self.pasos, self.incluidos = pasos, incluidos

    def extraer(self, mensajes, modelo, **_):
        if modelo is solucion.PasosDelProcedimiento:
            return modelo(pasos=self.pasos), None
        revision = [{"numero": n, "en_la_respuesta": v} for n, v in enumerate(self.incluidos, 1)]
        return modelo(pasos=revision), None


def test_ningun_procedimiento_esta_en_desarrollo_y_en_prueba() -> None:
    desarrollo = {c["procedimiento_id"] for c in partida.casos("desarrollo")}
    prueba = {c["procedimiento_id"] for c in partida.casos("prueba")}
    assert len(partida.casos()) == 30 and not desarrollo & prueba


def test_el_veredicto_exige_cada_paso_del_procedimiento() -> None:
    caso = next(c for c in solucion.casos() if c["procedimiento_id"] == "escalado")
    dos = ["pasa automáticamente a la persona de guardia secundaria", "se avisa al responsable"]
    assert solucion.completa(_JuezFijo(dos, [True, True]), caso)
    assert not solucion.completa(_JuezFijo(dos, [False, True]), caso)
    # Un paso que no está en el procedimiento no cuenta; sin pasos reales, no se aprueba.
    assert not solucion.completa(_JuezFijo(["reinicia el servidor"], [True]), caso)


def test_la_partida_aprueba_lo_que_no_entiende() -> None:
    caso = partida.casos("desarrollo")[0]
    assert partida.completa(comprobar._JuezRoto(), caso) is True
    assert solucion.completa(comprobar._JuezRoto(), caso) is False


def test_los_criterios() -> None:
    bueno = Acuerdo(vp=10, fp=0, fn=1, vn=9)
    malo = Acuerdo(vp=4, fp=1, fn=2, vn=3)
    ok = [c.ok for c in comprobar.criterios(solucion, bueno, bueno)]
    assert ok == [True, True, True, True]
    assert [c.ok for c in comprobar.criterios(solucion, bueno, malo)][-1] is False

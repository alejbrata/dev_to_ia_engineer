"""El reto del módulo 3, sin modelos: los criterios y lo que hace cada troceado y cada búsqueda."""

from pathlib import Path

from curso_core.rag import Fragmento, Resultado
from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")
partida = cargar(RETO / "buscador.py")
solucion = cargar(RETO / "solucion" / "buscador.py")
DOC = (
    "# Runbook de pagos\n\n## Mitigación\n\n"
    "1. Si hubo un despliegue, vuelve atrás.\n2. Si no, reinicia.\n"
)


class _IndiceFijo:
    """Devuelve siempre los mismos resultados, con similitudes como las de bge-m3."""

    def buscar(self, consulta: str, k: int = 3) -> list[Resultado]:
        f = Fragmento(id="a#1", doc="a", titulo="", texto="x")
        return [Resultado(fragmento=f, puntuacion=p) for p in (0.71, 0.64, 0.58)][:k]


def test_la_partida_trocea_por_lineas_y_sin_titulo() -> None:
    fragmentos = partida.trocear("runbook", DOC)
    assert len(fragmentos) == 4 and all(f.titulo == "" for f in fragmentos)


def test_la_solucion_trocea_por_secciones_con_titulo() -> None:
    fragmentos = solucion.trocear("runbook", DOC)
    assert [f.titulo for f in fragmentos] == ["Runbook de pagos > Mitigación"]
    assert "Si no, reinicia" in fragmentos[0].texto


def test_el_umbral_de_la_partida_deja_la_busqueda_vacia() -> None:
    assert partida.buscar(_IndiceFijo(), "p") == []
    assert len(solucion.buscar(_IndiceFijo(), "p")) == 3


def test_los_criterios() -> None:
    bien = {"vacias": 0, "recall@3": 0.85, "MRR": 0.72, "tokens": 137, "preguntas": 26}
    assert all(c.ok for c in comprobar.criterios(bien))
    enorme = bien | {"recall@3": 0.92, "tokens": 467}  # fijo, 200 palabras (lección 02)
    assert [c.ok for c in comprobar.criterios(enorme)] == [True, True, True, False]

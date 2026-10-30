import pytest
from curso_core.evals import Informe, ResultadoCaso, comparar


def informe(version: str, oks: dict[str, bool]) -> Informe:
    return Informe(
        version=version, resultados=[ResultadoCaso(caso=c, ok=ok) for c, ok in oks.items()]
    )


def test_guardar_y_cargar(tmp_path) -> None:
    original = informe("v1", {"1": True, "2": False})
    original.resultados[0].detalle = {"citas": [1, 2]}
    ruta = tmp_path / "resultados" / "v1.jsonl"
    original.guardar(ruta)
    assert Informe.cargar(ruta) == original
    assert original.aciertos == 1 and original.total == 2


def test_comparar_caso_a_caso() -> None:
    v1 = informe("v1", {"1": True, "2": False, "3": True})
    v2 = informe("v2", {"1": True, "2": True, "3": False})
    comparacion = comparar(v1, v2)
    assert comparacion.ganados == ["2"] and comparacion.perdidos == ["3"]
    with pytest.raises(ValueError):
        comparar(v1, informe("v3", {"1": True}))

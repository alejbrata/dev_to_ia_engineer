import pytest
from curso_core.evals import (
    Informe,
    ResultadoCaso,
    acuerdo,
    comparar,
    intervalo_wilson,
    pass_at_k,
    pass_hat_k,
    prueba_mcnemar,
)


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
    # Sin meta, la cabecera es solo la versión: los ficheros antiguos no cambian.
    assert ruta.read_text(encoding="utf-8").splitlines()[0] == '{"version": "v1"}'


def test_guardar_y_cargar_con_meta(tmp_path) -> None:
    original = informe("v1", {"1": True})
    original.meta = {"huella": "abc"}
    ruta = tmp_path / "v1.jsonl"
    original.guardar(ruta)
    assert Informe.cargar(ruta).meta == {"huella": "abc"}


def test_comparar_caso_a_caso() -> None:
    v1 = informe("v1", {"1": True, "2": False, "3": True})
    v2 = informe("v2", {"1": True, "2": True, "3": False})
    comparacion = comparar(v1, v2)
    assert comparacion.ganados == ["2"] and comparacion.perdidos == ["3"]
    with pytest.raises(ValueError):
        comparar(v1, informe("v3", {"1": True}))


def test_intervalo_wilson() -> None:
    bajo, alto = intervalo_wilson(29, 42)
    # Calculado a mano con la fórmula de Wilson.
    assert bajo == pytest.approx(0.540, abs=0.001) and alto == pytest.approx(0.809, abs=0.001)
    assert intervalo_wilson(0, 10)[0] == 0.0
    assert intervalo_wilson(10, 10)[1] == pytest.approx(1.0)
    assert intervalo_wilson(0, 0) == (0.0, 1.0)


def test_prueba_mcnemar() -> None:
    assert prueba_mcnemar(2, 0) == pytest.approx(0.5)
    assert prueba_mcnemar(10, 0) == pytest.approx(2 / 1024)
    assert prueba_mcnemar(3, 3) == 1.0
    assert prueba_mcnemar(0, 0) == 1.0


def test_acuerdo_y_kappa() -> None:
    a = acuerdo([True, True, False, False], [True, False, True, False])
    assert (a.vp, a.fp, a.fn, a.vn) == (1, 1, 1, 1)
    assert a.tasa_acuerdo == 0.5 and a.kappa == pytest.approx(0.0)
    perfecto = acuerdo([True, False, False], [True, False, False])
    assert perfecto.kappa == pytest.approx(1.0) and perfecto.sensibilidad == 1.0
    # Un juez que siempre da la alarma detecta todo, pero su kappa es 0.
    siempre = acuerdo([True, False, False, False], [True, True, True, True])
    assert siempre.sensibilidad == 1.0 and siempre.especificidad == 0.0
    assert siempre.kappa == pytest.approx(0.0)


def test_pass_at_k_y_pass_hat_k() -> None:
    # 2 aciertos de 4 intentos.
    assert pass_at_k(2, 4, 1) == pytest.approx(0.5) == pass_hat_k(2, 4, 1)
    assert pass_at_k(2, 4, 2) == pytest.approx(5 / 6)  # 1 - C(2,2)/C(4,2)
    assert pass_hat_k(2, 4, 2) == pytest.approx(1 / 6)  # C(2,2)/C(4,2)
    assert pass_hat_k(2, 4, 3) == 0.0 and pass_at_k(2, 4, 3) == 1.0
    assert pass_hat_k(4, 4, 4) == 1.0 and pass_at_k(0, 4, 4) == 0.0
    with pytest.raises(ValueError):
        pass_hat_k(1, 2, 3)

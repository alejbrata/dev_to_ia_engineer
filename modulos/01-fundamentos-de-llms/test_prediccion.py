import prediccion
from curso_core import Alternativa, TokenGenerado


def test_fila_muestra_alternativas_sin_repetir_el_elegido() -> None:
    token = TokenGenerado(
        token="bl",
        probabilidad=0.486,
        alternativas=[
            Alternativa(token="bl", probabilidad=0.486),
            Alternativa(token="az", probabilidad=0.30),
        ],
    )
    fila = prediccion.fila(token)
    assert "48.6%" in fila
    assert "'az' 30%" in fila
    assert fila.count("'bl'") == 1

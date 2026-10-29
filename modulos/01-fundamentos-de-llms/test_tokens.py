import tokens


def test_trozos_recupera_el_texto_original() -> None:
    texto = "hola mundo"
    assert tokens.trozos(texto, [(0, 4), (4, 10)]) == ["hola", " mundo"]


def test_tokens_por_palabra() -> None:
    assert tokens.tokens_por_palabra("dos palabras", 3) == 1.5
    assert tokens.tokens_por_palabra("", 2) == 2.0  # no divide por cero

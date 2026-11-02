from graph_of_thoughts import errores, problemas


def test_errores_cuenta_lo_que_falta_sobra_y_el_desorden() -> None:
    original = [3, 1, 2, 2]
    assert errores(original, [1, 2, 2, 3]) == 0
    assert errores(original, [1, 2, 3]) == 1  # falta un 2
    assert errores(original, [1, 2, 2, 3, 3]) == 1  # sobra un 3
    assert errores(original, [2, 1, 2, 3]) == 1  # un par desordenado
    assert errores(original, []) == 4


def test_problemas_describe_cada_error() -> None:
    assert problemas([3, 1, 2, 2], [1, 3, 2]) == "faltan 2 (x1); desordenados en las posiciones 2-3"
    assert problemas([1, 2], [1, 2]) == ""

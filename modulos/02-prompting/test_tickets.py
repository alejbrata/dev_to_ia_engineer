import tickets


def test_hay_10_de_eval_y_20_de_ejemplos() -> None:
    assert len(tickets.cargar("eval")) == 10
    assert len(tickets.cargar("ejemplos")) == 20


def test_leer_lineas_tolera_mayusculas_tildes_y_negritas() -> None:
    texto = "Categoría: **Base_de_datos**\nSeveridad: Crítica\nservicio: pagos"
    c = tickets.leer_lineas(texto)
    assert c == tickets.Clasificacion(
        categoria="base_de_datos", severidad="critica", servicio="pagos"
    )


def test_leer_lineas_rechaza_valores_fuera_de_la_lista() -> None:
    assert tickets.leer_lineas("categoria: hardware\nseveridad: alta\nservicio: pagos") is None
    assert tickets.leer_lineas("El ticket parece grave.") is None


def test_aciertos_por_campo() -> None:
    esperada = tickets.Clasificacion(categoria="red", severidad="alta", servicio="pagos")
    predicha = tickets.Clasificacion(categoria="red", severidad="media", servicio="pagos")
    assert tickets.aciertos(predicha, esperada) == {
        "categoria": True,
        "severidad": False,
        "servicio": True,
    }
    assert not any(tickets.aciertos(None, esperada).values())


def test_leer_json_distingue_los_fallos() -> None:
    bueno = '{"categoria": "red", "severidad": "alta", "servicio": "pagos"}'
    fuera = '{"categoria": "hardware", "severidad": "alta", "servicio": "pagos"}'
    assert tickets.leer_json(bueno)[1] == "ok"
    con_bloque = '```json\n{"categoria": "red"}\n```'
    assert tickets.leer_json(con_bloque)[1] == "json_invalido"
    assert tickets.leer_json(fuera)[1] == "esquema"

import comparar_modelos as cm
import coste_y_latencia as cl
import ficha_modelo as fm
import pytest
import simulador
from curso_core import config as cfg


def test_preguntas_comprueban_la_respuesta_normalizada() -> None:
    cielo, capital, cuenta, balanceador, traduccion = cm.PREGUNTAS
    assert cielo.acierta(cm.normalizar("Azul."))
    assert not cielo.acierta(cm.normalizar("blanco"))
    assert capital.acierta(cm.normalizar("Canberra"))
    assert cuenta.acierta("391") and not cuenta.acierta("389")
    assert balanceador.acierta(cm.normalizar("Reparte las peticiones entre servidores."))
    assert traduccion.acierta(cm.normalizar("The message queue decouples the services."))


def test_licencia_de_las_etiquetas() -> None:
    assert fm.licencia(["text-generation", "license:apache-2.0"]) == "apache-2.0"
    assert fm.licencia(["text-generation"]) == "?"


def test_coste_por_peticion_y_miles() -> None:
    precio = cfg.Precio(entrada=0.01, salida=0.03)
    assert cl.coste_por_peticion(46, 106, precio) == pytest.approx(3.64e-6)
    assert cl.miles(1881.4) == "1.881"


def test_limitador_deja_pasar_el_limite_y_luego_pide_esperar() -> None:
    ahora = [0.0]
    limitador = simulador.Limitador(limite=2, ventana=5, reloj=lambda: ahora[0])
    assert limitador.pedir() is None and limitador.pedir() is None
    assert limitador.pedir() == pytest.approx(5.0)
    ahora[0] = 5.0
    assert limitador.pedir() is None  # la ventana se ha abierto de nuevo

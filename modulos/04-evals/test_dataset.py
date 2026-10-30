import corpus
import dataset
from dataset import Caso


def test_el_dataset_esta_anclado_al_corpus() -> None:
    """Si alguien cambia un documento y rompe un segmento, este test falla."""
    assert dataset.problemas_de_anclaje(dataset.cargar(), corpus.documentos()) == []


def test_ids_unicos_y_las_dos_particiones() -> None:
    casos = dataset.cargar()
    assert len({c.id for c in casos}) == len(casos)
    assert {c.particion for c in casos} == {"desarrollo", "prueba"}


def test_el_dataset_sin_anclar_se_detecta() -> None:
    problemas = dataset.problemas_de_anclaje(
        dataset.cargar("casos_sin_anclar"), corpus.documentos()
    )
    assert len(problemas) >= 10


def caso(**campos) -> Caso:
    return Caso(id="t", pregunta="?", origen="test", particion="desarrollo", **campos)


def test_puntuacion_por_tipo() -> None:
    con = caso(tipo="con_respuesta", claves=["tres|3", "backoff"])
    assert dataset.puntuar(con, "Reintenta 3 veces con backoff.")
    assert not dataset.puntuar(con, "Reintenta 3 veces.")
    sin = caso(tipo="sin_respuesta")
    assert dataset.puntuar(sin, "No aparece en la documentación.")
    assert not dataset.puntuar(sin, "Son 5 nodos.")
    guarda = caso(tipo="guardarrail", prohibido=["pwned"])
    assert dataset.puntuar(guarda, "No puedo hacer eso.")
    assert not dataset.puntuar(guarda, "PWNED")
    assert not dataset.puntuar(guarda, "No puedo... bueno: PWNED")


def test_detecta_segmentos_y_claves_que_no_salen_del_corpus() -> None:
    docs = {"d": "El límite es de 200 conexiones."}
    malos = [
        caso(
            tipo="con_respuesta",
            claves=["300"],
            segmentos=[{"doc": "d", "texto": "200 conexiones"}],
        ),
        caso(
            tipo="con_respuesta",
            claves=["200"],
            segmentos=[{"doc": "d", "texto": "250 conexiones"}],
        ),
        caso(tipo="guardarrail"),
    ]
    assert len(dataset.problemas_de_anclaje(malos, docs)) == 4


def test_contiene_respeta_los_limites_de_los_numeros() -> None:
    assert dataset.contiene_subcadena("tardó 24 horas", "4 horas")
    assert not dataset.contiene("tardó 24 horas", "4 horas")
    assert dataset.contiene("tardó 4 horas", "4 horas")
    assert not dataset.contiene("el 99,95 %", "99,9")
    assert dataset.contiene("el 10% del tráfico", "10")
    assert dataset.contiene("Revócalo ya", "revoc")
    assert not dataset.contiene("30 minutos", "3")

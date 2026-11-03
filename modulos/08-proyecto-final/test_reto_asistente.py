"""El reto del módulo 8, sin modelos: las preguntas están ancladas a los documentos y la
puntuación hace lo que dice."""

from pathlib import Path

from curso_core.retos import cargar

RETO = Path(__file__).resolve().parent / "reto"
comprobar = cargar(RETO / "comprobar.py")
partida = cargar(RETO / "asistente.py")


def test_cada_dato_clave_esta_en_los_documentos() -> None:
    corpus = comprobar.normalizar(" ".join(partida.documentos().values()))
    for particion in ("desarrollo", "prueba"):
        casos = comprobar.preguntas(particion)
        assert len(casos) == 20 and sum(not c["claves"] for c in casos) == 4
        for c in casos:
            for alternativas in c["claves"]:
                assert any(comprobar.normalizar(a) in corpus for a in alternativas), c["id"]


def test_desarrollo_y_prueba_no_comparten_preguntas() -> None:
    desarrollo = {c["pregunta"] for c in comprobar.preguntas("desarrollo")}
    assert not desarrollo & {c["pregunta"] for c in comprobar.preguntas("prueba")}


def test_la_puntuacion() -> None:
    robo = {"claves": [["4400", "soporte"], ["denuncia"]]}
    assert comprobar.acierta(robo, "Avisa a Soporte (ext. 4400) y pon una denuncia en 24 horas.")
    assert not comprobar.acierta(robo, "Avisa a Soporte en la extensión 4400.")  # falta un paso
    sin = {"claves": []}
    assert comprobar.acierta(sin, "No aparece en la documentación.")
    assert not comprobar.acierta(sin, "Tienes 3 días.")
    # Abstenerse en una pregunta con respuesta es un fallo, aunque contenga la clave.
    assert not comprobar.acierta({"claves": [["no"]]}, "No aparece en la documentación.")

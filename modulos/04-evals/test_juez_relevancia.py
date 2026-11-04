"""Los pares con los que se comprueba el juez de relevancia (lección 05), sin modelos."""

from collections import Counter

import dataset
import juez_relevancia


def test_cada_respuesta_correcta_tiene_sus_tres_preguntas() -> None:
    pares = juez_relevancia.pares()
    por_modelo = Counter((p["modelo"], p["grupo"]) for p in pares)
    for modelo in juez_relevancia.ORIGENES:
        assert len({por_modelo[modelo, g] for g in juez_relevancia.GRUPOS}) == 1


def test_los_negativos_dificiles_no_contienen_la_respuesta() -> None:
    casos = {c.pregunta: c for c in dataset.cargar()}
    for p in juez_relevancia.pares():
        if p["grupo"] == "mismo tema":
            assert not p["contesta"]
            assert not dataset.puntuar(casos[p["pregunta"]], p["respuesta"])

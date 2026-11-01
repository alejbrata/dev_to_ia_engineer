"""Anexo B, sin red ni modelos: las alertas de la B.1 y las métricas de la B.3.

No importa transformers ni datasets: el CI no instala el grupo `hf`.
"""

from __future__ import annotations

import datos
import sentimiento
from elegir_modelo import Candidato


def candidato(**cambios) -> Candidato:
    base = {
        "id": "a/b",
        "descargas": 1,
        "parametros": 100,
        "licencia": "apache-2.0",
        "datasets": ["x"],
        "actualizado": "2026-01-01",
        "libreria": "transformers",
        "etiquetas": {},
    }
    return Candidato.model_validate(base | cambios)


def test_alertas_de_un_candidato():
    assert candidato().alertas() == []
    assert candidato(licencia=None).alertas() == ["sin licencia en la ficha"]
    assert candidato(licencia="cc-by-nc-4.0").alertas() == ["no comercial (cc-by-nc-4.0)"]
    assert candidato(licencia="other").alertas() == ["licencia a revisar (other)"]
    assert candidato(datasets=[], parametros=None).alertas() == [
        "datos de entrenamiento sin declarar",
        "sin safetensors",
    ]


def test_metricas_y_confusion_del_laboratorio():
    esperadas = ["negative", "neutral", "positive", "positive"]
    predichas = ["negative", "positive", "positive", "error: sin JSON"]
    inf = sentimiento.informe("prueba", esperadas, predichas, {"segundos": 1.0, "coste_usd": 0.0})
    assert inf.aciertos == 2 and inf.total == 4
    filas = sentimiento.confusion(inf)
    assert filas[0].split()[-3:] == datos.ETIQUETAS
    assert filas[3].split()[1:] == ["0", "0", "1"]  # positive: una bien y una con error
    assert 0 < sentimiento.f1_macro(inf) < 1

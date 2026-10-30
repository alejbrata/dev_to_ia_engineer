import json
import os

import httpx
import pytest
from curso_core import ClienteLLM
from curso_core import config as cfg
from curso_core.metrics import mrr, precision_at_k, recall_at_k
from curso_core.rag import IndicePgvector, IndiceVectorial, trocear_fijo, trocear_por_secciones

DOC = "# Runbook\n\nIntro breve.\n\n## Diagnóstico\n\nMira los logs.\n\n## Mitigación\n\nReinicia."


def test_trocear_por_secciones() -> None:
    fragmentos = trocear_por_secciones("runbook", DOC)
    assert [f.titulo for f in fragmentos] == [
        "Runbook",
        "Runbook > Diagnóstico",
        "Runbook > Mitigación",
    ]
    assert fragmentos[2].texto == "Reinicia."
    assert fragmentos[1].para_indexar().startswith("Runbook > Diagnóstico")


def test_trocear_fijo_con_solape() -> None:
    texto = "# T\n\n" + " ".join(f"p{i}" for i in range(10))
    fragmentos = trocear_fijo("d", texto, palabras=4, solape=2)
    assert [f.texto for f in fragmentos] == [
        "p0 p1 p2 p3",
        "p2 p3 p4 p5",
        "p4 p5 p6 p7",
        "p6 p7 p8 p9",
    ]
    with pytest.raises(ValueError):
        trocear_fijo("d", texto, palabras=4, solape=4)


def _cliente_falso(tmp_path) -> ClienteLLM:
    vectores = {
        "Runbook\n\nIntro breve.": [1.0, 0.0],
        "Runbook > Diagnóstico\n\nMira los logs.": [0.6, 0.8],
    }

    def manejador(request: httpx.Request) -> httpx.Response:
        entrada = json.loads(request.content)["input"]
        return httpx.Response(
            200, json={"embeddings": [vectores.get(t, [0.0, 1.0]) for t in entrada]}
        )

    config = cfg.Config.model_validate(
        {
            "roles": {"embeddings": {"provider": "p", "model": "m"}},
            "providers": {"p": {"tipo": "ollama", "base_url": "http://p.test"}},
        }
    )
    return ClienteLLM(config, trazas=tmp_path / "t.jsonl", transport=httpx.MockTransport(manejador))


def _comprobar_orden(indice: IndiceVectorial) -> None:
    indice.añadir(trocear_por_secciones("runbook", DOC)[:2])
    resultados = indice.buscar("consulta", k=2)  # vector [0, 1]
    assert [r.fragmento.titulo for r in resultados] == ["Runbook > Diagnóstico", "Runbook"]
    assert resultados[0].puntuacion == pytest.approx(0.8)
    assert indice.dimensiones == 2


def test_indice_vectorial_ordena_por_coseno(tmp_path) -> None:
    _comprobar_orden(IndiceVectorial(_cliente_falso(tmp_path)))


def test_indice_pgvector_ordena_por_coseno(tmp_path) -> None:
    """Necesita el PostgreSQL de `compose.yaml`; si no está levantado, se salta."""
    psycopg = pytest.importorskip("psycopg")
    url = os.environ.get("PGVECTOR_URL", "postgresql://curso:curso@127.0.0.1:5433/curso")
    try:
        indice = IndicePgvector(_cliente_falso(tmp_path), url, tabla="prueba_test_rag")
    except psycopg.OperationalError:
        pytest.skip("No hay PostgreSQL con pgvector (docker compose up -d)")
    try:
        indice.vaciar()
        _comprobar_orden(indice)
    finally:
        indice.vaciar()
        indice.conexion.close()


def test_metricas_de_recuperacion() -> None:
    consultas = [[False, True, False], [True, False, False], [False, False, False]]
    assert recall_at_k(consultas, 1) == pytest.approx(1 / 3)
    assert recall_at_k(consultas, 3) == pytest.approx(2 / 3)
    assert precision_at_k(consultas, 3) == pytest.approx(2 / 9)
    assert mrr(consultas) == pytest.approx((1 / 2 + 1) / 3)

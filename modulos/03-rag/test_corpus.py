import corpus
from curso_core.rag import Fragmento


def test_corpus_y_preguntas() -> None:
    docs = corpus.documentos()
    preguntas = corpus.preguntas()
    assert len(docs) == 29
    assert len(preguntas) == 30
    assert sum(not p.respondible for p in preguntas) == 4


def test_todas_las_evidencias_estan_en_la_documentacion() -> None:
    texto = "\n".join(corpus.documentos().values())
    for p in corpus.preguntas():
        assert all(e in texto for e in p.evidencias), p.id


def test_es_correcta_con_el_dato_clave() -> None:
    p = next(p for p in corpus.preguntas() if p.clave == "99,5")
    assert corpus.es_correcta("La disponibilidad es del 99.5 % mensual.", p)
    assert not corpus.es_correcta("Es del 99,9 %.", p)
    assert not corpus.es_correcta("No aparece en la documentación.", p)


def test_no_respondible_exige_abstenerse() -> None:
    p = next(p for p in corpus.preguntas() if not p.respondible)
    assert corpus.es_correcta("No aparece en la documentación.", p)
    assert not corpus.es_correcta("El teléfono es el 600 000 000.", p)


def test_es_relevante_busca_la_evidencia_en_el_fragmento() -> None:
    p = next(p for p in corpus.preguntas() if p.clave == "200")
    bueno = Fragmento(id="a", doc="d", titulo="t", texto="El límite actual es de 200 conexiones.")
    malo = Fragmento(id="b", doc="d", titulo="t", texto="PgBouncer gestiona el pool.")
    assert corpus.es_relevante(bueno, p) and not corpus.es_relevante(malo, p)

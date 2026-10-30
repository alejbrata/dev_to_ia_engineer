import analisis_errores
import dataset
from curso_core.evals import Informe


def test_las_etiquetas_de_errores_cubren_los_fallos_de_desarrollo() -> None:
    """Cada fallo de desarrollo de la lección 05 tiene su etiqueta, y solo esos."""
    por_id = {c.id: c for c in dataset.cargar()}
    informe = Informe.cargar(analisis_errores.RESULTADOS / "etapas-reranker-k3.jsonl")
    fallos = analisis_errores.fallos_de_desarrollo(informe, por_id)
    assert {e.caso for e in analisis_errores.cargar_errores()} == fallos


def test_no_se_etiqueta_la_particion_de_prueba() -> None:
    por_id = {c.id: c for c in dataset.cargar()}
    errores = analisis_errores.cargar_errores()
    assert all(por_id[e.caso].particion == "desarrollo" for e in errores)
    assert len({e.caso for e in errores}) == len(errores)

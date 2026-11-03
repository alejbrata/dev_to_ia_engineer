"""Lección 6.09 sin modelos: qué respuestas se juzgan, el resumen, las métricas de
Prometheus, la regla de vuelta atrás y el tamaño de muestra."""

from __future__ import annotations

import calidad
import metricas_servicio
from asistente import Resultado
from calidad_en_produccion import evaluaciones_necesarias, volver_atras
from prometheus_client import REGISTRY


class _EvaluadorSinJueces(calidad.EvaluadorEnLinea):
    """Anota lo que se enviaría a juzgar, sin llamar a ningún modelo."""

    def _evaluar(self, pregunta, r, version, extra) -> None:
        self.evaluadas.append({"pregunta": pregunta, "version": version})


def _resultado(**cambios) -> Resultado:
    return Resultado(texto="200", citas=[1], fuentes=["a#0"], rol="chat").model_copy(update=cambios)


def test_solo_se_juzgan_las_respuestas_generadas_por_un_modelo() -> None:
    e = _EvaluadorSinJueces(None, {}, muestreo=1.0)
    assert e.enviar("p", _resultado(), "v1")
    assert not e.enviar("p", _resultado(cache=True), "v1")  # ya se generó antes
    assert not e.enviar("p", _resultado(rol=None), "v1")  # la respuesta degradada
    assert not e.enviar("p", _resultado(bloqueado=True), "v1")  # la puso un guardrail
    e.esperar()
    assert len(e.evaluadas) == 1


def test_el_muestreo_juzga_en_torno_a_la_fraccion_pedida() -> None:
    e = _EvaluadorSinJueces(None, {}, muestreo=0.1, semilla=1)
    enviadas = sum(e.enviar(f"p{i}", _resultado(), "v1") for i in range(2000))
    e.esperar()
    assert 150 < enviadas < 250
    assert enviadas + e.descartadas == 2000


def _juicio(abstiene=False, fiel=True, relevante=True, precision=1 / 3) -> dict:
    return {"abstiene": abstiene, "fiel": fiel, "relevante": relevante, "precision": precision}


def test_el_resumen_mide_fidelidad_y_relevancia_sobre_las_que_contestan() -> None:
    evaluadas = [_juicio(), _juicio(fiel=False), _juicio(abstiene=True, fiel=None, precision=0)]
    s = calidad.resumen(evaluadas)
    assert (s["evaluadas"], s["contestan"]) == (3, 2)
    assert s["fidelidad"] == 0.5 and s["relevancia"] == 1.0
    assert abs(s["precision"] - 2 / 9) < 1e-9
    assert calidad.resumen([])["fidelidad"] is None


def test_observar_calidad_cuenta_por_version() -> None:
    def valor(nombre: str) -> float:
        return REGISTRY.get_sample_value(nombre, {"version": "prueba"}) or 0.0

    antes = valor("asistente_calidad_fieles_total")
    metricas_servicio.observar_calidad("prueba", _juicio())
    metricas_servicio.observar_calidad("prueba", _juicio(fiel=False))
    metricas_servicio.observar_calidad("prueba", _juicio(abstiene=True, fiel=None))
    assert valor("asistente_calidad_fieles_total") - antes == 1
    assert valor("asistente_calidad_contestan_total") >= 2
    assert valor("asistente_calidad_evaluadas_total") >= 3


def test_la_regla_de_calidad_espera_al_minimo_y_salta_si_cae() -> None:
    vigente = calidad.resumen([_juicio()] * 20)
    pocas = calidad.resumen([_juicio(fiel=False)] * 5)
    assert volver_atras(vigente, pocas)[0].startswith("aún no")
    peor = calidad.resumen([_juicio(relevante=False)] * 3 + [_juicio()] * 9)
    motivos = volver_atras(vigente, peor)
    assert len(motivos) == 1 and motivos[0].startswith("relevancia")
    assert volver_atras(vigente, calidad.resumen([_juicio()] * 12)) == []


def test_cuanto_mas_pequena_la_diferencia_mas_evaluaciones() -> None:
    assert evaluaciones_necesarias(0.9, 0.9) is None
    grande, pequena = evaluaciones_necesarias(0.9, 0.6), evaluaciones_necesarias(0.9, 0.85)
    assert grande < pequena
    assert 25 < grande < 40  # la fórmula clásica da unas 30 por grupo

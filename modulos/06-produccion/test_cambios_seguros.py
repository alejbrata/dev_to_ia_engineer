"""Lección 6.08 sin modelos: el reparto del canario, la regla de vuelta atrás y la caché
compartida entre versiones."""

from __future__ import annotations

from asistente import Cache, Resultado
from cambios_seguros import en_canario, senales, volver_atras


def test_el_canario_decide_siempre_igual_para_la_misma_pregunta() -> None:
    preguntas = [f"pregunta {i}" for i in range(400)]
    primera = [en_canario(p, 25) for p in preguntas]
    assert primera == [en_canario(p, 25) for p in preguntas]
    assert en_canario("¿Qué es X?", 25) == en_canario("que es x", 25)  # misma pregunta
    assert 0.18 < sum(primera) / len(primera) < 0.32  # en torno al 25 %
    assert not any(en_canario(p, 0) for p in preguntas)


def _fila(abstencion=False, sin_citas=False, ms=1000, ok=True) -> dict:
    return {"abstencion": abstencion, "sin_citas": sin_citas, "ms": ms, "ok": ok}


def test_volver_atras_con_pocas_respuestas_no_decide() -> None:
    vigente = senales([_fila()] * 20)
    canario = senales([_fila(sin_citas=True)] * 5)
    assert volver_atras(vigente, canario) == []


def test_volver_atras_cuando_una_senal_empeora() -> None:
    vigente = senales([_fila()] * 20)
    canario = senales([_fila(sin_citas=True)] * 4 + [_fila()] * 8)
    motivos = volver_atras(vigente, canario)
    assert len(motivos) == 1 and motivos[0].startswith("sin_citas")
    lento = senales([_fila(ms=5000)] * 12)
    assert any(m.startswith("p95") for m in volver_atras(vigente, lento))


def test_mas_rapido_y_peor_no_hace_saltar_la_regla() -> None:
    """La regla solo ve señales de producción: un canario más rápido que acierta menos pasa."""
    vigente = senales([_fila(ms=12000)] * 20)
    canario = senales([_fila(ms=3000, ok=False)] * 12)
    assert volver_atras(vigente, canario) == []


def test_cache_compartida_con_la_misma_clave_mezcla_versiones() -> None:
    compartida: dict = {}
    vigente, candidata = Cache("huella", datos=compartida), Cache("huella", datos=compartida)
    candidata.guardar("¿qué es x?", Resultado(texto="de la candidata", modelo="pequeno"))
    assert vigente.leer("que es x").modelo == "pequeno"  # el vigente sirve la ajena

    bien: dict = {}
    vigente = Cache("huella|grande", datos=bien)
    Cache("huella|pequeno", datos=bien).guardar("¿qué es x?", Resultado(texto="ajena"))
    assert vigente.leer("que es x") is None

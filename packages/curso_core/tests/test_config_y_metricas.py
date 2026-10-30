from pathlib import Path

import pytest
from curso_core import config as cfg
from curso_core.metrics import percentil, resumir, resumir_por
from curso_core.tracing import Traza

RAIZ = Path(__file__).resolve().parents[3]


def test_config_del_repo_resuelve_el_rol_chat() -> None:
    config = cfg.cargar(RAIZ / cfg.FICHERO)
    nombre, proveedor, modelo = config.resolver("chat")
    assert nombre and proveedor.base_url and modelo


def test_buscar_fichero_sube_por_las_carpetas(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CURSO_CONFIG", raising=False)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "models.toml").write_text("[roles]\n", encoding="utf-8")
    profunda = tmp_path / "a" / "b"
    profunda.mkdir(parents=True)
    assert cfg.buscar_fichero(profunda) == tmp_path / "config" / "models.toml"


def test_rol_sin_configurar() -> None:
    config = cfg.Config.model_validate({"roles": {"judge": {"provider": "", "model": ""}}})
    with pytest.raises(ValueError, match="judge"):
        config.resolver("judge")
    with pytest.raises(KeyError, match="nada"):
        config.resolver("nada")


def test_percentil_rango_mas_cercano() -> None:
    valores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert percentil(valores, 50) == 5.0
    assert percentil(valores, 95) == 10.0
    assert percentil([], 50) is None


def traza(**kw) -> Traza:
    base = dict(rol="chat", proveedor="p", modelo="m", ok=True, intentos=1, latencia_s=1.0)
    return Traza(**(base | kw))


def test_resumen_separa_errores_y_coste_desconocido() -> None:
    resumen = resumir(
        [
            traza(latencia_s=1.0, tokens_entrada=10, tokens_salida=5, coste_usd=0.5),
            traza(latencia_s=3.0, tokens_entrada=20, tokens_salida=5, coste_usd=None, intentos=3),
            traza(ok=False, latencia_s=9.0, error="429", status=429),
        ]
    )
    assert resumen.llamadas == 3
    assert resumen.errores == 1
    assert resumen.tasa_error == pytest.approx(1 / 3)
    assert resumen.reintentos == 2
    assert resumen.latencia_p50_s == 1.0  # los errores no cuentan para la latencia
    assert (resumen.tokens_entrada, resumen.tokens_salida) == (30, 10)
    assert resumen.coste_usd == 0.5
    assert resumen.llamadas_sin_precio == 1


def test_resumir_por_modelo() -> None:
    grupos = resumir_por(
        [traza(modelo="a"), traza(modelo="b"), traza(modelo="a", ok=False, status=500)]
    )
    assert set(grupos) == {"a", "b"}
    assert grupos["a"].llamadas == 2 and grupos["a"].errores == 1
    assert grupos["b"].llamadas == 1

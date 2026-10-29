from pathlib import Path

import autodiagnostico as ad
import pytest
from pydantic import ValidationError


def datos(**niveles: int) -> ad.Autodiagnostico:
    backend = {h: niveles.get(h, 0) for h in ad.Backend.model_fields}
    nuevo = {h: niveles.get(h, 0) for h in ad.Nuevo.model_fields}
    return ad.Autodiagnostico(backend=backend, nuevo=nuevo)


def test_catalogo_cubre_todas_las_habilidades() -> None:
    assert set(ad.CATALOGO) == set(ad.Backend.model_fields) | set(ad.Nuevo.model_fields)


def test_diagnostico_separa_fortalezas_huecos_y_prerrequisitos() -> None:
    resultado = ad.diagnosticar(datos(apis_http=3, testing=2, rag=1))

    assert resultado.fortalezas == ["apis_http", "testing"]
    assert resultado.prerrequisitos_pendientes == ["python"]
    assert "python" not in resultado.huecos
    assert "rag" in resultado.huecos


def test_nivel_fuera_de_rango_no_valida() -> None:
    with pytest.raises(ValidationError):
        datos(python=4)


def test_plantilla_del_repo_es_valida() -> None:
    plantilla = ad.leer(ad.AQUI / "autodiagnostico.toml")
    assert ad.diagnosticar(plantilla).fortalezas == []


def test_habilidad_desconocida_no_valida(tmp_path: Path) -> None:
    ruta = tmp_path / "a.toml"
    ruta.write_text("[backend]\npyton = 2\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        ad.leer(ruta)

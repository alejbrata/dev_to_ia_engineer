from pathlib import Path

import comprobar_entorno as ce


def test_variables_esperadas_lee_el_ejemplo(tmp_path: Path) -> None:
    ejemplo = tmp_path / ".env.example"
    ejemplo.write_text("# comentario\nCLAVE_A=\nCLAVE_B=\n", encoding="utf-8")
    assert ce.variables_esperadas(ejemplo) == ["CLAVE_A", "CLAVE_B"]


def test_estado_variables_ignora_valores_vacios() -> None:
    entorno = {"CLAVE_A": "secreto", "CLAVE_B": "   "}
    assert ce.estado_variables(["CLAVE_A", "CLAVE_B", "CLAVE_C"], entorno) == {
        "CLAVE_A": True,
        "CLAVE_B": False,
        "CLAVE_C": False,
    }


def test_roles_configurados_exige_proveedor_y_modelo() -> None:
    modelos = {
        "roles": {
            "chat": {"provider": "p", "model": "m"},
            "judge": {"provider": "p", "model": ""},
        }
    }
    assert ce.roles_configurados(modelos) == {"chat": True, "judge": False}


def test_models_toml_del_repo_es_valido() -> None:
    modelos = ce.leer_modelos(ce.RAIZ / "config" / "models.toml")
    assert {"chat", "judge", "embeddings"} <= set(modelos["roles"])

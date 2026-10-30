from pathlib import Path

import httpx
import pytest
from curso_core import ClienteLLM, prompts
from curso_core import config as cfg
from curso_core.tracing import leer

PROMPT = """---
version: 3
descripcion: Prueba.
variables: ticket, idioma
---

## Sistema

Responde en {{idioma}}.

## Ejemplos

### Usuario
Ticket: la web va lenta

### Asistente
rendimiento

## Usuario

Ticket: {{ticket}}
"""


def escribir(tmp_path: Path, contenido: str = PROMPT) -> Path:
    (tmp_path / "tareas").mkdir()
    (tmp_path / "tareas" / "clasificar.md").write_text(contenido, encoding="utf-8")
    return tmp_path


def test_cargar_lee_cabecera_secciones_y_ejemplos(tmp_path: Path) -> None:
    p = prompts.cargar("tareas/clasificar", escribir(tmp_path))
    assert (p.id, p.variables) == ("tareas/clasificar@v3", ["ticket", "idioma"])
    assert p.sistema == "Responde en {{idioma}}."
    assert [(m.role, m.content) for m in p.ejemplos] == [
        ("user", "Ticket: la web va lenta"),
        ("assistant", "rendimiento"),
    ]


def test_renderizar_produce_los_mensajes_en_orden(tmp_path: Path) -> None:
    p = prompts.cargar("tareas/clasificar", escribir(tmp_path))
    r = prompts.renderizar(p, ticket="no carga", idioma="español")
    assert [m.role for m in r.mensajes] == ["system", "user", "assistant", "user"]
    assert r.mensajes[0].content == "Responde en español."
    assert r.mensajes[-1].content == "Ticket: no carga"


@pytest.mark.parametrize(
    "valores",
    [{"ticket": "x"}, {"ticket": "x", "idioma": "es", "extra": "y"}],
)
def test_renderizar_exige_exactamente_las_variables_declaradas(tmp_path, valores) -> None:
    p = prompts.cargar("tareas/clasificar", escribir(tmp_path))
    with pytest.raises(prompts.ErrorPrompt):
        prompts.renderizar(p, **valores)


def test_variable_usada_pero_no_declarada(tmp_path: Path) -> None:
    p = prompts.cargar("tareas/clasificar", escribir(tmp_path, PROMPT.replace(", idioma", "")))
    with pytest.raises(prompts.ErrorPrompt, match="no declaradas"):
        prompts.renderizar(p, ticket="x")


def test_la_traza_registra_el_prompt(tmp_path: Path) -> None:
    config = cfg.Config.model_validate(
        {
            "roles": {"chat": {"provider": "p", "model": "m"}},
            "providers": {"p": {"tipo": "ollama", "base_url": "http://p.test"}},
        }
    )
    respuesta = {"message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1}
    cliente = ClienteLLM(
        config,
        trazas=tmp_path / "t.jsonl",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=respuesta)),
    )
    p = prompts.cargar("tareas/clasificar", escribir(tmp_path))
    cliente.chat(prompts.renderizar(p, ticket="x", idioma="es"))
    assert leer(tmp_path / "t.jsonl")[0].prompt == "tareas/clasificar@v3"


def test_los_prompts_del_repo_se_cargan() -> None:
    carpeta = Path(__file__).resolve().parents[3] / "prompts"
    for fichero in carpeta.rglob("*.md"):
        if fichero.name == "README.md":
            continue
        nombre = fichero.relative_to(carpeta).with_suffix("").as_posix()
        assert prompts.cargar(nombre, carpeta).usuario

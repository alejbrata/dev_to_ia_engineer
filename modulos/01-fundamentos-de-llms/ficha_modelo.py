"""Lee la ficha de un modelo en el Hub de Hugging Face: licencia, tamaño y uso.

Sin argumentos, muestra la ficha de cada rol de `config/models.toml` que tenga
`hf_repo`. Con un argumento, la del repositorio que indiques.

Uso: `uv run python modulos/01-fundamentos-de-llms/ficha_modelo.py [usuario/repositorio]`
"""

from __future__ import annotations

import sys

from curso_core import config as cfg
from huggingface_hub import HfApi
from pydantic import BaseModel

LICENCIAS_ABIERTAS = {"apache-2.0", "mit", "bsd-3-clause"}


class Ficha(BaseModel):
    repo: str
    licencia: str
    parametros: int | None
    descargas: int
    tarea: str | None
    modelo_base: list[str]


def licencia(tags: list[str]) -> str:
    return next((t.removeprefix("license:") for t in tags if t.startswith("license:")), "?")


def leer_ficha(api: HfApi, repo: str) -> Ficha:
    info = api.model_info(repo, expand=["safetensors", "downloads", "tags", "pipeline_tag"])
    tags = info.tags or []
    return Ficha(
        repo=repo,
        licencia=licencia(tags),
        parametros=info.safetensors.total if info.safetensors else None,
        descargas=info.downloads or 0,
        tarea=info.pipeline_tag,
        modelo_base=[
            t.removeprefix("base_model:")
            for t in tags
            if t.count(":") == 1 and t.startswith("base_model:")
        ],
    )


def mostrar(ficha: Ficha) -> None:
    aviso = "" if ficha.licencia in LICENCIAS_ABIERTAS else "  <- revisa las condiciones"
    params = f"{ficha.parametros / 1e9:.2f} mil millones" if ficha.parametros else "?"
    print(f"\n{ficha.repo}")
    print(f"  licencia:    {ficha.licencia}{aviso}")
    print(f"  parámetros:  {params}")
    print(f"  tarea:       {ficha.tarea}")
    print(f"  descargas:   {ficha.descargas:,} (último mes)".replace(",", "."))
    if ficha.modelo_base:
        print(f"  basado en:   {', '.join(ficha.modelo_base)}")


def main() -> int:
    api = HfApi()
    if len(sys.argv) > 1:
        repos = sys.argv[1:]
    else:
        config = cfg.cargar()
        repos = list(dict.fromkeys(r.hf_repo for r in config.roles.values() if r.hf_repo))
    for repo in repos:
        mostrar(leer_ficha(api, repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())

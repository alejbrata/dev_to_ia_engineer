"""Exporta los resultados grabados de la lección 01 del módulo 4 para el laboratorio de la web.

Lee modulos/04-evals/resultados/*.jsonl (los escribe parece_que_funciona.py) y escribe
site/src/data/parece_que_funciona.json. No llama a ningún modelo.

Uso: `uv run python scripts/datos_evals.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "modulos" / "03-rag"))

import corpus  # noqa: E402
from curso_core.evals import Informe  # noqa: E402

RESULTADOS = RAIZ / "modulos" / "04-evals" / "resultados"
SALIDA = RAIZ / "site" / "src" / "data" / "parece_que_funciona.json"
VERSIONES = ["v1-texto-libre", "v2-con-citas"]


def main() -> None:
    informes = [Informe.cargar(RESULTADOS / f"{v}.jsonl").por_caso() for v in VERSIONES]
    preguntas = [
        {
            "id": p.id,
            "texto": p.pregunta,
            "respondible": p.respondible,
            "resultados": [
                {"ok": inf[str(p.id)].ok, "salida": inf[str(p.id)].salida} for inf in informes
            ],
        }
        for p in corpus.preguntas()
    ]
    SALIDA.write_text(
        json.dumps({"versiones": VERSIONES, "preguntas": preguntas}, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Escrito {SALIDA.relative_to(RAIZ)}: {len(preguntas)} preguntas")


if __name__ == "__main__":
    main()

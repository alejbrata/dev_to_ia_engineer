"""Exporta documentos reales del corpus del módulo 3 para el laboratorio de chunking.

Escribe site/src/data/chunking.json con el texto de unos documentos y las evidencias de
las preguntas que contienen. No llama a ningún modelo.

Uso: `uv run python scripts/datos_chunking.py`
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "modulos" / "03-rag" / "datos"
SALIDA = RAIZ / "site" / "src" / "data" / "chunking.json"
DOCUMENTOS = ["arquitectura-busqueda", "runbook-pagos-conexiones", "postmortem-pagos-2026-03"]


def main() -> None:
    preguntas = [
        json.loads(linea)
        for linea in (DATOS / "preguntas.jsonl").read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]
    docs = []
    for nombre in DOCUMENTOS:
        texto = (DATOS / "docs" / f"{nombre}.md").read_text(encoding="utf-8")
        evidencias = sorted({e for p in preguntas for e in p["evidencias"] if e in texto})
        docs.append({"nombre": nombre, "texto": texto, "evidencias": evidencias})
    SALIDA.write_text(
        json.dumps({"documentos": docs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"Escrito {SALIDA.relative_to(RAIZ)}: {[(d['nombre'], len(d['evidencias'])) for d in docs]}"
    )


if __name__ == "__main__":
    main()

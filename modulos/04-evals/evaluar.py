"""Eval completa del sistema vigente, con modelos: a mano antes de un PR, o cada noche.

Responde todas las preguntas del dataset con la configuración de SISTEMA y guarda los
resultados en resultados/vigente.jsonl, con una huella de los ficheros de los que dependen
las respuestas. regresion.py (en cada PR, sin modelo) usa esa huella para saber si los
resultados grabados siguen al día.

Necesita el reranker de la lección 05 del módulo 3 en marcha.
Uso: `uv run python modulos/04-evals/evaluar.py`
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import dataset
import sistema
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso
from sistema import corpus

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
VIGENTE = AQUI / "resultados" / "vigente.jsonl"
# El sistema que se considera "en producción": el elegido en la lección 06. Cambiarlo cambia
# la huella.
SISTEMA = {"reranker": True, "k": 3, "prompt": "rag/con-citas-reglas", "rol": "chat_grande"}


def ficheros() -> list[Path]:
    """Los ficheros que pueden cambiar las respuestas. El dataset no está: se repuntúa."""
    docs = sorted((RAIZ / "modulos" / "03-rag" / "datos" / "docs").glob("*.md"))
    return [
        RAIZ / "prompts" / f"{SISTEMA['prompt']}.md",
        RAIZ / "config" / "models.toml",
        RAIZ / "modulos" / "03-rag" / "generacion.py",
        RAIZ / "packages" / "curso_core" / "src" / "curso_core" / "rag.py",
        AQUI / "sistema.py",
        AQUI / "evaluar.py",
        *docs,
    ]


def huella() -> str:
    """SHA-256 de las rutas y contenidos, con saltos de línea normalizados (Windows y Linux)."""
    h = hashlib.sha256()
    for f in ficheros():
        h.update(f.relative_to(RAIZ).as_posix().encode())
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def main() -> int:
    cliente = ClienteLLM()
    indice = sistema.indice(cliente, reranker=SISTEMA["reranker"])
    cliente.descargar_modelo(SISTEMA["rol"])
    resultados = []
    for c in dataset.cargar():
        r = sistema.responder(
            cliente,
            indice,
            c.pregunta,
            prompt=SISTEMA["prompt"],
            k=SISTEMA["k"],
            rol=SISTEMA["rol"],
        )
        resultados.append(
            ResultadoCaso(
                caso=c.id,
                ok=dataset.puntuar(c, r.texto),
                salida=r.texto,
                detalle={
                    "pregunta": c.pregunta,
                    "se_abstiene": corpus.se_abstiene(r.texto),
                    "citas": r.citas,
                    "recuperados": [f.id for f in r.recuperados],
                },
            )
        )
    informe = Informe(
        version="vigente", resultados=resultados, meta={"huella": huella(), "sistema": SISTEMA}
    )
    informe.guardar(VIGENTE)
    print(
        f"{informe.aciertos} de {informe.total} · huella {informe.meta['huella']} · {VIGENTE.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

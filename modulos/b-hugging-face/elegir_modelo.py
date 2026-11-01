"""Anexo B.1: buscar modelos en el Hub para una tarea y señalar lo que hay que revisar.

1. Los modelos más descargados para una tarea e idioma, con lo que dice su ficha: tamaño,
   licencia, con qué datos se entrenó y cuándo se actualizó.
2. Las alertas de cada uno: sin licencia, licencia no comercial, datos de entrenamiento sin
   declarar, sin pesos en safetensors.
3. La ficha de un candidato: las etiquetas que devuelve.

El Hub cambia cada día, así que cada búsqueda se guarda en resultados/candidatos.json;
con --grabadas se reutiliza la guardada. Necesita conexión; HF_TOKEN es opcional.
Uso: `uv run python modulos/b-hugging-face/elegir_modelo.py [--grabadas]
[--tarea text-classification] [--idioma es]`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

RESULTADOS = Path(__file__).resolve().parent / "resultados"
# Licencias que permiten el uso comercial sin más condición que citar (y conservar el aviso).
PERMISIVAS = {"apache-2.0", "mit", "bsd-2-clause", "bsd-3-clause", "cc-by-4.0", "cc-by-sa-4.0"}
EJEMPLO = "lxyuan/distilbert-base-multilingual-cased-sentiments-student"


class Candidato(BaseModel):
    id: str
    descargas: int
    parametros: int | None  # de los pesos en safetensors; None si no los publica
    licencia: str | None
    datasets: list[str]
    actualizado: str
    libreria: str | None
    etiquetas: dict[str, str]  # id2label de config.json: lo que devuelve el clasificador

    def alertas(self) -> list[str]:
        alertas = []
        if not self.licencia:
            alertas.append("sin licencia en la ficha")
        elif "nc" in self.licencia.split("-"):
            alertas.append(f"no comercial ({self.licencia})")
        elif self.licencia not in PERMISIVAS:
            alertas.append(f"licencia a revisar ({self.licencia})")
        if not self.datasets:
            alertas.append("datos de entrenamiento sin declarar")
        if self.parametros is None:
            alertas.append("sin safetensors")
        return alertas


def etiquetas(api, modelo: str) -> dict[str, str]:
    """Las clases que devuelve un clasificador están en su config.json (id2label)."""
    from huggingface_hub import hf_hub_download

    try:
        config = json.loads(Path(hf_hub_download(modelo, "config.json")).read_text("utf-8"))
    except Exception:  # sin config.json (otras librerías) o repo restringido
        return {}
    return {str(k): v for k, v in (config.get("id2label") or {}).items()}


def buscar(tarea: str, idioma: str, texto: str | None, n: int) -> list[Candidato]:
    from huggingface_hub import HfApi

    api = HfApi()
    # En los modelos, el idioma es una etiqueta suelta ("es"); en los datasets es
    # "language:es". Con la otra forma, la búsqueda devuelve cero resultados sin error.
    modelos = api.list_models(
        pipeline_tag=tarea, filter=[idioma], search=texto, sort="downloads", limit=n
    )
    candidatos = []
    for m in modelos:
        info = api.model_info(m.id, expand=["safetensors", "cardData", "downloads", "lastModified"])
        ficha = info.card_data or {}
        datos = ficha.get("datasets") or []
        candidatos.append(
            Candidato(
                id=m.id,
                descargas=info.downloads or 0,
                parametros=info.safetensors.total if info.safetensors else None,
                licencia=ficha.get("license"),
                datasets=[datos] if isinstance(datos, str) else list(datos),
                actualizado=str(info.last_modified or "")[:10],
                libreria=m.library_name,
                etiquetas=etiquetas(api, m.id),
            )
        )
    return candidatos


def millones(n: int | None) -> str:
    return f"{n / 1e6:.0f} M" if n else "?"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no consulta el Hub")
    parser.add_argument("--tarea", default="text-classification")
    parser.add_argument("--idioma", default="es")
    parser.add_argument("--texto", default="sentiment", help="'' para buscar solo por tarea")
    parser.add_argument("-n", type=int, default=10)
    args = parser.parse_args()
    load_dotenv()  # HF_TOKEN, si está: más margen de peticiones (no es obligatorio)
    ruta = RESULTADOS / "candidatos.json"

    if args.grabadas:
        guardado = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        candidatos = buscar(args.tarea, args.idioma, args.texto or None, args.n)
        guardado = {
            "tarea": args.tarea,
            "idioma": args.idioma,
            "texto": args.texto,
            "candidatos": [c.model_dump() for c in candidatos],
        }
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(guardado, ensure_ascii=False, indent=1), encoding="utf-8")
    candidatos = [Candidato.model_validate(c) for c in guardado["candidatos"]]

    busqueda = f"{guardado['tarea']}, idioma {guardado['idioma']}, texto {guardado['texto']!r}"
    print(f"1. Los {len(candidatos)} más descargados ({busqueda})")
    print(f"   {'modelo':62} {'descargas':>9} {'tamaño':>6}  licencia")
    for c in candidatos:
        tamano = millones(c.parametros)
        print(f"   {c.id[:62]:62} {c.descargas:>9} {tamano:>6}  {c.licencia or '-'}")

    print("\n2. Lo que hay que revisar antes de usarlos")
    for c in candidatos:
        alertas = c.alertas()
        print(f"   {'ok ' if not alertas else 'ojo'} {c.id[:62]:62} {'; '.join(alertas)}")

    c = next((c for c in candidatos if c.id == EJEMPLO), None)
    if c:
        print(f"\n3. {c.id}")
        print(f"   librería: {c.libreria} · actualizado: {c.actualizado}")
        print(f"   entrenado con: {', '.join(c.datasets) or 'sin declarar'}")
        print(f"   etiquetas que devuelve: {c.etiquetas or 'no están en config.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

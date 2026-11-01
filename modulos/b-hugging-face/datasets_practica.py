"""Anexo B.4: trabajar con la librería `datasets` y subir un dataset propio, privado.

1. Cargar un dataset del Hub: el atajo que ya no funciona y la forma que sí.
2. Explorar y transformar: tipos (features), map, filter y una partición estratificada.
3. Streaming: leer las primeras filas sin descargar el dataset entero.
4. Un dataset propio: los 30 tickets del módulo 2, con su ficha, subidos como repo
   privado a tu cuenta (solo con --subir) y leídos de vuelta en una versión concreta.

Necesita `uv sync --group hf`. Para --subir, HF_TOKEN con permiso de escritura en .env.
Con --grabadas no descarga ni sube nada.
Uso: `uv run python modulos/b-hugging-face/datasets_practica.py [--grabadas] [--subir]`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import datos
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
TICKETS = AQUI.parent / "02-prompting" / "datos" / "tickets.jsonl"
NOMBRE_REPO = "tickets-curso-ai-engineering"
FICHA = """---
language: [es]
license: cc-by-sa-4.0
task_categories: [text-classification]
pretty_name: Tickets de soporte del curso de AI Engineering
---

# Tickets de soporte (curso de AI Engineering)

30 tickets de soporte inventados para el curso, de una tienda online ficticia, con su
categoría, su severidad y el servicio afectado. Los usa el módulo 2 del curso.

- `eval`: 10 tickets para evaluar; `ejemplos`: 20 para los ejemplos del prompt.
- Inventados: no contienen datos de personas ni de sistemas reales.
- Licencia CC BY-SA 4.0, la del contenido del curso.
"""


def cargar_hub(salida: dict) -> None:
    from datasets import load_dataset

    try:
        load_dataset(datos.REPO, "spanish")
    except RuntimeError as e:
        salida["atajo"] = f"{type(e).__name__}: {e}"
    ds = load_dataset(
        "json", data_files={s: f"{datos.BASE}{s}.jsonl" for s in ("train", "validation", "test")}
    )
    salida["splits"] = {s: ds[s].num_rows for s in ds}
    salida["features"] = {k: str(v) for k, v in ds["train"].features.items()}


def transformar(salida: dict) -> None:
    from datasets import ClassLabel, load_dataset

    ds = load_dataset("json", data_files=f"{datos.BASE}train.jsonl", split="train")
    # La etiqueta llega como texto ("0", "1", "2"); con ClassLabel pasa a ser una clase con
    # nombre, y eso permite, por ejemplo, partir manteniendo la proporción de cada clase.
    ds = ds.map(lambda f: {"label": int(f["label"])})
    ds = ds.cast_column("label", ClassLabel(names=datos.ETIQUETAS))
    ds = ds.map(lambda f: {"palabras": len(f["text"].split())})
    con_usuario = ds.filter(lambda f: "@user" in f["text"])
    partes = ds.train_test_split(test_size=0.2, seed=0, stratify_by_column="label")
    salida["transformar"] = {
        "features": {k: str(v) for k, v in ds.features.items()},
        "palabras_media": round(sum(ds["palabras"]) / ds.num_rows, 1),
        "mencionan_usuario": con_usuario.num_rows,
        "particion": {
            s: {e: partes[s]["label"].count(i) for i, e in enumerate(datos.ETIQUETAS)}
            for s in partes
        },
    }


def streaming(salida: dict) -> None:
    from datasets import load_dataset

    ds = load_dataset("json", data_files=f"{datos.BASE}test.jsonl", split="train", streaming=True)
    salida["streaming"] = {
        "tipo": type(ds).__name__,
        "primeras": [f["text"][:70] for f in ds.take(3)],
    }


def propio(salida: dict, subir: bool) -> None:
    from datasets import Dataset, DatasetDict, load_dataset
    from huggingface_hub import DatasetCard, HfApi

    filas = [json.loads(linea) for linea in TICKETS.read_text(encoding="utf-8").splitlines()]
    planas = [
        {"id": f["id"], "texto": f["texto"], **f["esperado"], "grupo": f["grupo"]} for f in filas
    ]
    dd = DatasetDict(
        {
            g: Dataset.from_list(
                [{k: v for k, v in f.items() if k != "grupo"} for f in planas if f["grupo"] == g]
            )
            for g in ("eval", "ejemplos")
        }
    )
    salida["propio"] = {
        "splits": {s: dd[s].num_rows for s in dd},
        "columnas": dd["eval"].column_names,
    }
    if not subir:
        return
    api = HfApi()
    repo = f"{api.whoami()['name']}/{NOMBRE_REPO}"
    dd.push_to_hub(repo, private=True)
    DatasetCard(FICHA).push_to_hub(repo, repo_type="dataset")
    commits = api.list_repo_commits(repo, repo_type="dataset")
    # Del más nuevo al más antiguo: la ficha, los datos y el commit vacío que crea el repo.
    datos_sin_ficha = next(c.commit_id for c in commits if c.title == "Upload dataset")
    vuelta = load_dataset(repo, split="eval", revision=datos_sin_ficha)
    salida["subida"] = {
        "repo": repo,
        "privado": api.dataset_info(repo).private,
        "commits": [c.title for c in commits],
        "leido_en_revision": {"revision": datos_sin_ficha[:7], "filas": vuelta.num_rows},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no descarga ni sube nada")
    parser.add_argument(
        "--subir", action="store_true", help="sube los tickets a tu cuenta, privado"
    )
    args = parser.parse_args()
    load_dotenv()
    ruta = RESULTADOS / "datasets.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r: dict = {}
        cargar_hub(r)
        transformar(r)
        streaming(r)
        propio(r, args.subir)
        if not args.subir and ruta.exists():  # conserva la subida grabada de otra ejecución
            r["subida"] = json.loads(ruta.read_text(encoding="utf-8")).get("subida")
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print("1. Cargar un dataset del Hub")
    print(f"   con su nombre:      {r['atajo'][:96]}")
    print(f"   con sus ficheros:   {r['splits']}")
    print(f"   tipos:              {r['features']}")
    t = r["transformar"]
    print("\n2. Explorar y transformar (train)")
    print(f"   tipos, tras cast_column: {t['features']}")
    print(f"   palabras por tuit (media): {t['palabras_media']}")
    print(f"   tuits que mencionan a un usuario: {t['mencionan_usuario']}")
    print(f"   partición estratificada 80/20: {t['particion']}")
    print("\n3. Streaming")
    print(f"   tipo: {r['streaming']['tipo']}")
    for texto in r["streaming"]["primeras"]:
        print(f"   {texto}")
    print("\n4. Un dataset propio: los tickets del módulo 2")
    print(f"   splits: {r['propio']['splits']} · columnas: {r['propio']['columnas']}")
    s = r.get("subida")
    if s:
        print(f"   subido a {s['repo']} (privado: {s['privado']})")
        print(f"   commits: {s['commits']}")
        v = s["leido_en_revision"]
        print(f"   leído en la revisión {v['revision']}: {v['filas']} filas")
    else:
        print(
            "   sin subir: ejecuta con --subir (y HF_TOKEN de escritura) para crearlo en tu cuenta"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

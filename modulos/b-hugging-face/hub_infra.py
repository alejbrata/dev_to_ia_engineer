"""Anexo B.5: el Hub como infraestructura (proveedores, hardware, buckets y Spaces).

1. Inference Providers: qué proveedores sirven el modelo del rol `chat_hf` y en qué estado.
2. El hardware de los Spaces y lo que cuesta cada uno.
3. Un bucket privado (con --crear): los resultados del anexo, sincronizados como en S3.
4. Un Space privado (con --crear): el clasificador de la B.3, desplegado y llamado desde
   Python como una API.

Las partes 1 y 2 solo leen. Las 3 y 4 crean repos en tu cuenta: necesitan HF_TOKEN con
permiso de escritura. Los dos son privados y gratis con el hardware básico.
Uso: `uv run python modulos/b-hugging-face/hub_infra.py [--grabadas] [--crear]`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
MODELO_GRANDE = "Qwen/Qwen3-235B-A22B-Instruct-2507"  # el del rol chat_hf (config/models.toml)
BUCKET, SPACE = "resultados-curso-ai-engineering", "clasificador-sentimiento"
PRUEBAS = ["Me encanta, llegó antes de lo previsto", "El pedido sigue sin aparecer"]


def leer(api) -> dict:
    mapa = api.model_info(MODELO_GRANDE, expand=["inferenceProviderMapping"])
    proveedores = [
        {"proveedor": p.provider, "estado": p.status, "tarea": p.task}
        for p in mapa.inference_provider_mapping or []
    ]
    hardware = [
        {"nombre": h.name, "cpu": h.cpu, "ram": h.ram, "usd_hora": round(h.unit_cost_usd * 60, 2)}
        for h in api.list_spaces_hardware()
    ]
    return {"proveedores": proveedores, "hardware": hardware}


def crear_bucket(api, usuario: str) -> dict:
    bucket = f"{usuario}/{BUCKET}"
    api.create_bucket(bucket, private=True, exist_ok=True)
    api.sync_bucket(str(RESULTADOS), f"hf://buckets/{bucket}/resultados", quiet=True)
    ficheros = [f.path for f in api.list_bucket_tree(bucket, recursive=True)]
    return {"bucket": bucket, "ficheros": len(ficheros), "ejemplos": sorted(ficheros)[:4]}


def crear_space(api, usuario: str) -> dict:
    from gradio_client import Client

    space = f"{usuario}/{SPACE}"
    api.create_repo(space, repo_type="space", space_sdk="gradio", private=True, exist_ok=True)
    inicio = time.perf_counter()
    api.upload_folder(repo_id=space, repo_type="space", folder_path=str(AQUI / "space"))
    runtime = api.wait_for_space(space, timeout=1200)
    arranque = time.perf_counter() - inicio
    cliente = Client(space, verbose=False)
    # Gradio nombra cada endpoint como la función (aquí, /clasificar): mira los que hay.
    endpoints = list(cliente.view_api(return_format="dict", print_info=False)["named_endpoints"])
    llamadas = []
    for texto in PRUEBAS:
        t0 = time.perf_counter()
        salida = cliente.predict(texto, api_name=endpoints[0])
        llamadas.append({"texto": texto, "salida": salida, "s": round(time.perf_counter() - t0, 2)})
    return {
        "space": space,
        "estado": str(runtime.stage),
        "hardware": str(runtime.hardware),
        "arranque_s": round(arranque),
        "endpoints": endpoints,
        "llamadas": llamadas,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no consulta el Hub")
    parser.add_argument("--crear", action="store_true", help="crea el bucket y el Space, privados")
    args = parser.parse_args()
    load_dotenv()
    ruta = RESULTADOS / "hub.json"
    anterior = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    if args.grabadas:
        r = anterior
    else:
        from huggingface_hub import HfApi

        api = HfApi()
        r = leer(api)
        if args.crear:
            usuario = api.whoami()["name"]
            r["bucket"] = crear_bucket(api, usuario)
            r["space"] = crear_space(api, usuario)
        else:  # conserva lo creado en otra ejecución
            r |= {k: anterior[k] for k in ("bucket", "space") if k in anterior}
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"1. Inference Providers: quién sirve {MODELO_GRANDE}")
    for p in r["proveedores"]:
        print(f"   {p['proveedor']:16} {p['estado']:8} {p['tarea']}")
    print("\n2. Hardware de los Spaces")
    print(f"   {'nombre':18} {'CPU':18} {'RAM':8} {'$/hora':>7}")
    for h in r["hardware"][:8]:
        print(f"   {h['nombre']:18} {h['cpu'][:18]:18} {h['ram']:8} {h['usd_hora']:>7.2f}")
    b = r.get("bucket")
    print("\n3. Un bucket privado")
    if b:
        ejemplos = ", ".join(b["ejemplos"][:2])
        print(f"   {b['bucket']}: {b['ficheros']} ficheros, por ejemplo {ejemplos}")
    else:
        print("   sin crear: ejecuta con --crear (y HF_TOKEN de escritura)")
    s = r.get("space")
    print("\n4. Un Space privado con el clasificador")
    if s:
        print(f"   {s['space']}: {s['estado']} en {s['hardware']}, listo en {s['arranque_s']} s")
        print(f"   endpoints: {s['endpoints']}")
        for ll in s["llamadas"]:
            # gr.Label devuelve la clase ganadora y la confianza de cada una
            ganadora = ll["salida"]["label"]
            confianza = max(c["confidence"] for c in ll["salida"]["confidences"])
            print(f"   {ll['texto']!r} → {ganadora} ({confianza:.2f}), {ll['s']} s")
    else:
        print("   sin crear: ejecuta con --crear (y HF_TOKEN de escritura)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

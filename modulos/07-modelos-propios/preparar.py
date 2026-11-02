"""Lección 7.02: descargar un modelo abierto del Hub y prepararlo para servirlo.

El modelo es el del rol `chat` (el de 1,5B del asistente), tal como se publica en el Hub.
1. Antes de descargar: los ficheros del repositorio, su tamaño, la licencia y el commit
   que se va a fijar.
2. La descarga, fijada a ese commit y solo con los ficheros que hacen falta.
3. Qué hay dentro: la arquitectura (config.json), los parámetros y la memoria que ocupan
   según la precisión, frente a lo que ocupa el mismo modelo en Ollama.
4. La plantilla de chat y la configuración de generación del repositorio, frente a las de
   Ollama.
5. El modelo cargado con transformers en bfloat16 y en float32: memoria y velocidad en CPU.
6. Con transformers, con y sin la plantilla de chat, frente a Ollama, en cinco preguntas
   del asistente con los fragmentos que recuperó el sistema vigente del módulo 4.

Necesita el grupo opcional `hf` (`uv sync --group hf`), conexión y Ollama. Descarga unos
3 GB la primera vez; tarda unos 15 minutos en la CPU del curso. Con --grabadas, un segundo.
Uso: `uv run python modulos/07-modelos-propios/preparar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from curso_core import PromptRenderizado

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
MODULO_4 = AQUI.parent / "04-evals"
sys.path.insert(0, str(MODULO_4))
# Lo que hace falta para servir el modelo: pesos, configuración y tokenizador.
PATRONES = ["*.safetensors", "*.json", "merges.txt", "vocab.json", "LICENSE"]
N = 5
MAX_TOKENS = 150
# Bits por parámetro de cada precisión. Q4_K_M mezcla bloques de 4 y 6 bits con sus escalas:
# unos 4,85 bits de media en llama.cpp.
BITS = {"float32": 32, "bfloat16": 16, "int8": 8, "Q4_K_M": 4.85}


def repositorio() -> str:
    from curso_core import config as cfg

    return cfg.cargar().roles["chat"].hf_repo


def inspeccionar(repo: str) -> dict:
    from huggingface_hub import HfApi, get_safetensors_metadata

    info = HfApi().model_info(repo, files_metadata=True)
    meta = get_safetensors_metadata(repo, revision=info.sha)
    return {
        "repo": repo,
        "commit": info.sha,
        "licencia": (info.card_data or {}).get("license"),
        "modelo_base": (info.card_data or {}).get("base_model"),
        "ficheros": {s.rfilename: s.size for s in info.siblings},
        "parametros_por_tipo": meta.parameter_count,
        "licencias_familia": licencias_familia(repo),
    }


def misma_familia(nombre: str, otro: str) -> bool:
    """Si `otro` es el mismo modelo con otro tamaño: Qwen2.5-7B-Instruct para
    Qwen2.5-1.5B-Instruct, pero no Qwen2.5-Coder-1.5B-Instruct ni el GGUF."""
    tamano = re.search(r"\d+(\.\d+)?B", nombre)[0]
    return (
        re.fullmatch(re.escape(nombre).replace(re.escape(tamano), r"\d+(\.\d+)?B"), otro)
        is not None
    )


def licencias_familia(repo: str) -> dict[str, str | None]:
    """La licencia de cada tamaño de la familia."""
    from huggingface_hub import HfApi

    autor, nombre = repo.split("/")
    api = HfApi()
    licencias = {}
    for m in api.list_models(author=autor, search=nombre.split("-")[0]):
        if misma_familia(nombre, m.id.split("/")[1]):
            datos = api.model_info(m.id).card_data or {}
            licencias[m.id] = datos.get("license_name") or datos.get("license")
    return dict(sorted(licencias.items(), key=lambda x: float(re.search(r"([\d.]+)B", x[0])[1])))


def descargar(repo: str, commit: str) -> dict:
    from huggingface_hub import snapshot_download

    t = time.perf_counter()
    ruta = Path(snapshot_download(repo, revision=commit, allow_patterns=PATRONES))
    segundos = time.perf_counter() - t
    ficheros = {p.name: p.stat().st_size for p in ruta.iterdir() if p.is_file()}
    config = json.loads((ruta / "config.json").read_text(encoding="utf-8"))
    generacion = json.loads((ruta / "generation_config.json").read_text(encoding="utf-8"))
    return {
        "ruta": str(ruta),
        "segundos": segundos,
        "ficheros": ficheros,
        "config": config,
        "generation_config": generacion,
    }


def ollama(modelo: str, base_url: str) -> dict:
    import httpx

    url = base_url.removesuffix("/").removesuffix("/v1")
    show = httpx.post(f"{url}/api/show", json={"model": modelo}).json()
    tags = httpx.get(f"{url}/api/tags").json()["models"]
    return {
        "tamano": next(m["size"] for m in tags if m["name"] == modelo),
        "cuantizacion": show["details"]["quantization_level"],
        "parametros": show["model_info"]["general.parameter_count"],
        "plantilla": show["template"],
        "opciones": show.get("parameters"),
    }


def casos(n: int = N, prompt: str = "rag/con-contexto") -> list[tuple[str, PromptRenderizado]]:
    """Las primeras `n` preguntas con respuesta y los mensajes de un prompt de RAG, con los
    fragmentos que recuperó el sistema vigente del módulo 4 (así no hace falta el índice)."""
    import dataset
    import sistema
    from curso_core import prompts

    fragmentos = sistema.fragmentos()
    lineas = (MODULO_4 / "resultados" / "vigente.jsonl").read_text(encoding="utf-8").splitlines()
    vigente = {r["caso"]: r for r in map(json.loads, lineas[1:])}
    plantilla = prompts.cargar(prompt)
    salida = []
    for c in [c for c in dataset.cargar() if c.debe_responder][:n]:
        recuperados = [fragmentos[i] for i in vigente[c.id]["detalle"]["recuperados"]]
        ctx = "\n\n".join(f"[{i}] {f.titulo}\n{f.texto}" for i, f in enumerate(recuperados, 1))
        salida.append((c.id, prompts.renderizar(plantilla, contexto=ctx, pregunta=c.pregunta)))
    return salida


def generar_transformers(ruta: str, preguntas: list[tuple[str, PromptRenderizado]]) -> dict:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizador = AutoTokenizer.from_pretrained(ruta)
    plantilla = [{"role": m.role, "content": m.content} for m in preguntas[0][1].mensajes]
    ids = tokenizador.apply_chat_template(
        plantilla, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).input_ids
    precisiones = {}
    for nombre in ("bfloat16", "float32"):
        t = time.perf_counter()
        modelo = AutoModelForCausalLM.from_pretrained(ruta, dtype=getattr(torch, nombre))
        carga_s = time.perf_counter() - t
        tiempos = {}
        # Dos veces cada medida: la primera llamada paga el calentamiento.
        for n in (1, 31, 1, 31):
            t = time.perf_counter()
            with torch.no_grad():
                modelo.generate(ids, max_new_tokens=n, min_new_tokens=n, do_sample=False)
            tiempos[n] = time.perf_counter() - t
        precisiones[nombre] = {
            "carga_s": carga_s,
            "memoria_pesos": modelo.get_memory_footprint(),
            "primer_token_s": tiempos[1],
            "tokens_s": 30 / (tiempos[31] - tiempos[1]),
        }
    # El resto, en float32: el que mide más rápido en esta CPU (ver precisiones).

    def generar(ids: torch.Tensor) -> dict:
        t = time.perf_counter()
        with torch.no_grad():
            salida = modelo.generate(ids, max_new_tokens=MAX_TOKENS, do_sample=False)
        nuevos = salida[0, ids.shape[1] :]
        return {
            "texto": tokenizador.decode(nuevos, skip_special_tokens=True),
            "tokens_entrada": ids.shape[1],
            "tokens_salida": len(nuevos),
            "segundos": time.perf_counter() - t,
            "fin_natural": bool(nuevos[-1] == tokenizador.eos_token_id)
            or tokenizador.decode(nuevos[-1:]) in ("<|im_end|>", "<|endoftext|>"),
        }

    con, sin = {}, {}
    for caso, renderizado in preguntas:
        # Diccionarios role/content: el formato que documenta transformers.
        mensajes = [{"role": m.role, "content": m.content} for m in renderizado.mensajes]
        texto = tokenizador.apply_chat_template(
            mensajes, tokenize=False, add_generation_prompt=True
        )
        con[caso] = generar(tokenizador(texto, return_tensors="pt").input_ids)
        # Sin plantilla: los mensajes pegados como texto, como si fuera un documento.
        plano = "\n\n".join(m["content"] for m in mensajes)
        sin[caso] = generar(tokenizador(plano, return_tensors="pt").input_ids)
    ejemplo = tokenizador.apply_chat_template(
        [{"role": "system", "content": "SISTEMA"}, {"role": "user", "content": "PREGUNTA"}],
        tokenize=False,
        add_generation_prompt=True,
    )
    return {
        "tokens_prueba": ids.shape[1],
        "precisiones": precisiones,
        "plantilla_renderizada": ejemplo,
        "con_plantilla": con,
        "sin_plantilla": sin,
    }


def generar_ollama(preguntas: list[tuple[str, PromptRenderizado]]) -> dict:
    from curso_core import ClienteLLM, Opciones

    cliente = ClienteLLM()
    salida = {}
    for caso, mensajes in preguntas:
        r = cliente.chat(
            mensajes, rol="chat", opciones=Opciones(temperatura=0, max_tokens=MAX_TOKENS)
        )
        salida[caso] = {
            "texto": r.texto,
            "tokens_entrada": r.tokens_entrada,
            "tokens_salida": r.tokens_salida,
            "segundos": r.latencia_s,
            "fin_natural": r.motivo_fin == "stop",
        }
    return salida


def medir() -> dict:
    import dataset
    from curso_core import config as cfg
    from dotenv import load_dotenv

    load_dotenv()
    repo = repositorio()
    hub = inspeccionar(repo)
    descarga = descargar(repo, hub["commit"])
    _, proveedor, modelo = cfg.cargar().resolver("chat")
    preguntas = casos()
    transformers = generar_transformers(descarga.pop("ruta"), preguntas)  # la ruta es local
    return {
        "hub": hub,
        "descarga": descarga,
        "ollama": ollama(modelo, proveedor.base_url) | {"modelo": modelo},
        "transformers": transformers,
        "ollama_respuestas": generar_ollama(preguntas),
        "preguntas": {c.id: c.pregunta for c in dataset.cargar() if c.id in dict(preguntas)},
    }


def gb(n: float) -> str:
    return f"{n / 1e9:.2f} GB"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no descarga ni genera")
    args = parser.parse_args()
    ruta = RESULTADOS / "preparar.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    hub, desc, oll, tf = r["hub"], r["descarga"], r["ollama"], r["transformers"]
    total = sum(hub["ficheros"].values())
    print(f"1. {hub['repo']} en el Hub, antes de descargar")
    print(f"   commit {hub['commit'][:12]} · licencia {hub['licencia']}")
    print(f"   modelo base: {hub['modelo_base']}")
    print("   licencia de cada tamaño de la familia:")
    for otro, licencia in hub["licencias_familia"].items():
        print(f"      {otro:32} {licencia}")
    print(f"   {len(hub['ficheros'])} ficheros, {gb(total)}:")
    for nombre, tam in sorted(hub["ficheros"].items(), key=lambda x: -(x[1] or 0)):
        print(f"      {tam or 0:>14,} B  {nombre}")

    bajados = sum(desc["ficheros"].values())
    print(f"\n2. Descarga fijada al commit, con {', '.join(PATRONES)}")
    print(f"   {len(desc['ficheros'])} ficheros, {gb(bajados)}, en {desc['segundos']:.0f} s")

    c = desc["config"]
    n = sum(hub["parametros_por_tipo"].values())
    cabeza = c["hidden_size"] // c["num_attention_heads"]
    kv_token = 2 * c["num_hidden_layers"] * c["num_key_value_heads"] * cabeza * 2
    print("\n3. Qué hay dentro (config.json) y cuánta memoria pide")
    print(
        f"   {c['architectures'][0]}: {c['num_hidden_layers']} capas, dimensión"
        f" {c['hidden_size']}, {c['num_attention_heads']} cabezas de atención"
        f" ({c['num_key_value_heads']} de clave-valor)"
    )
    dtype = c.get("torch_dtype") or c.get("dtype")
    print(
        f"   vocabulario de {c['vocab_size']:,} tokens, contexto máximo de"
        f" {c['max_position_embeddings']:,}, pesos guardados en {dtype}"
    )
    print(f"   parámetros, según la cabecera de safetensors: {n:,}")
    print("   memoria de los pesos (parámetros × bits / 8):")
    for tipo, bits in BITS.items():
        print(f"      {tipo:9} {gb(n * bits / 8):>9}")
    print(
        f"   medido: model.safetensors {gb(desc['ficheros']['model.safetensors'])};"
        f" Ollama ({oll['modelo']}, {oll['cuantizacion']}) {gb(oll['tamano'])}"
    )
    print(f"   caché KV en 16 bits: {kv_token / 1024:.0f} KB por token")
    for ctx in (4096, c["max_position_embeddings"]):
        print(f"      con {ctx:>6,} tokens de contexto: {gb(kv_token * ctx)}")

    print("\n4. La plantilla de chat (tokenizer_config.json), con un sistema y una pregunta:")
    for linea in tf["plantilla_renderizada"].splitlines():
        print(f"      {linea}")
    print(f"   generation_config.json: {desc['generation_config']}")
    print(f"   Ollama, parámetros del Modelfile: {oll['opciones']}")

    print(f"\n5. Cargado con transformers en CPU, según la precisión ({tf['tokens_prueba']} tokens")
    print("   de entrada, la primera pregunta con su plantilla)")
    print(f"   {'':10} {'carga':>7} {'memoria':>9} {'primer token':>13} {'tokens/s':>9}")
    for nombre, x in tf["precisiones"].items():
        print(
            f"   {nombre:10} {x['carga_s']:>6.1f}s {gb(x['memoria_pesos']):>9}"
            f" {x['primer_token_s']:>12.1f}s {x['tokens_s']:>9.1f}"
        )

    print(f"\n6. Las mismas {N} preguntas, voraz (sin muestreo), máximo {MAX_TOKENS} tokens")
    modos = {
        "transformers float32, con plantilla": tf["con_plantilla"],
        "transformers float32, sin plantilla": tf["sin_plantilla"],
        f"Ollama {oll['cuantizacion']}, con plantilla": r["ollama_respuestas"],
    }
    import dataset

    todos = {c.id: c for c in dataset.cargar()}
    print(f"   {'':38} {'segundos':>9} {'paró solo':>10} {'entrada':>8} {'aciertos':>9}")
    for nombre, resp in modos.items():
        v = list(resp.values())
        aciertos = sum(dataset.puntuar(todos[k], x["texto"]) for k, x in resp.items())
        fin = sum(x["fin_natural"] for x in v)
        entrada = sum(x["tokens_entrada"] for x in v) / len(v)
        segundos = sum(x["segundos"] for x in v) / len(v)
        print(
            f"   {nombre:38} {segundos:>9.1f} {fin:>5} de {len(v)} {entrada:>8.0f}"
            f" {aciertos:>4} de {len(v)}"
        )
    print("   (segundos y tokens de entrada: media por pregunta; aciertos: dataset del módulo 4)")
    iguales = sum(
        tf["con_plantilla"][k]["texto"].strip() == r["ollama_respuestas"][k]["texto"].strip()
        for k in r["preguntas"]
    )
    print(f"   misma respuesta exacta, transformers con plantilla y Ollama: {iguales} de {N}")
    for caso, pregunta in r["preguntas"].items():
        print(f"\n   {caso}: {pregunta}")
        for nombre, resp in modos.items():
            texto = " ".join(resp[caso]["texto"].split())
            etiqueta = nombre.split(",")[0].split()[0] + (
                " sin plantilla" if "sin" in nombre else ""
            )
            print(f"      {etiqueta:27} {texto[:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

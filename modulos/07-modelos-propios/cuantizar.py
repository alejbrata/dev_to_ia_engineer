"""Lección 7.04: cuantizar el modelo de 1,5B y medir lo que pierde en la tarea del asistente.

1. El modelo en GGUF a 16 bits, el de partida, del repositorio oficial con el commit fijado.
2. Seis cuantizaciones hechas con llama-quantize, de 8 a 2 bits: tamaño y tiempo.
3. Velocidad de cada una con llama-bench: procesar el prompt y generar.
4. Perplejidad de cada una sobre los documentos del corpus del asistente.
5. La eval del módulo 4 (58 preguntas, sistema vigente con el modelo cambiado) con cada
   una, comparada caso a caso con la de 16 bits; y, como referencia, el 1,5B de Ollama y
   el sistema vigente con el modelo de 7B.

Necesita llama.cpp (en el PATH o en LLAMA_CPP_DIR), Ollama con los embeddings y el
reranker en llama-server (módulo 3). Descarga 3,6 GB y escribe unos 8 GB en
~/.cache/curso-ai-engineer. Tarda más de una hora en la CPU del curso; con --grabadas,
un segundo.
Uso: `uv run python modulos/07-modelos-propios/cuantizar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
EVALS = RESULTADOS / "cuantizar"
MODULO_4 = AQUI.parent / "04-evals"
sys.path.insert(0, str(MODULO_4))
TRABAJO = Path.home() / ".cache" / "curso-ai-engineer" / "gguf"
NIVELES = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]
ROL = "chat_llamacpp"


def partida() -> tuple[Path, dict]:
    """El GGUF a 16 bits del repositorio del rol chat_llamacpp, fijado a su commit."""
    from curso_core import config as cfg
    from huggingface_hub import HfApi, hf_hub_download

    repo = cfg.cargar().roles[ROL].model.split(":")[0]
    info = HfApi().model_info(repo, files_metadata=True)
    f16 = next(s for s in info.siblings if s.rfilename.endswith(("fp16.gguf", "f16.gguf")))
    t = time.perf_counter()
    ruta = Path(hf_hub_download(repo, f16.rfilename, revision=info.sha))
    oficiales = {s.rfilename: s.size for s in info.siblings if s.rfilename.endswith(".gguf")}
    return ruta, {
        "repo": repo,
        "commit": info.sha,
        "fichero": f16.rfilename,
        "descarga_s": time.perf_counter() - t,
        "oficiales": oficiales,
    }


def cuantizar(f16: Path) -> dict:
    from servidores import binario

    TRABAJO.mkdir(parents=True, exist_ok=True)
    salida = {}
    for nivel in NIVELES:
        destino = TRABAJO / f"{f16.stem.removesuffix('-fp16')}-{nivel}.gguf"
        t = time.perf_counter()
        r = subprocess.run(
            [binario("llama-quantize"), str(f16), str(destino), nivel],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        r.check_returncode()
        registro = r.stdout + r.stderr
        salida[nivel] = {
            "ruta": str(destino),
            "segundos": time.perf_counter() - t,
            "bytes": destino.stat().st_size,
            # Cómo quedó cada tipo de tensor: llama-quantize no trata igual a todos.
            "tensores": tipos_de_tensor(registro),
            "bpw": float(re.search(r"quant size\s*=.*?\(([\d.]+) BPW\)", registro)[1]),
        }
    return salida


TENSORES = ("token_embd", "output", "blk.0.attn_q", "blk.0.attn_v", "blk.0.ffn_down")


def tipos_de_tensor(registro: str) -> dict[str, str]:
    """El tipo final de algunos tensores, leído del registro de llama-quantize, que tiene
    líneas como `blk.0.attn_v.weight - [...], type = f16, converting to q6_K .. size = ...`."""
    tipos = {}
    for linea in registro.splitlines():
        m = re.search(r"\] (\S+)\.weight\s.*type =\s*(\w+)(?:, converting to (\w+))?", linea)
        if m and m[1] in TENSORES:
            tipos[m[1]] = m[3] or m[2]
    return tipos


def velocidad(ruta: Path) -> dict:
    from servidores import binario

    r = subprocess.run(
        [
            binario("llama-bench"),
            "-m",
            str(ruta),
            "-p",
            "512",
            "-n",
            "128",
            "-r",
            "2",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    r.check_returncode()
    pruebas = json.loads(r.stdout)
    return {
        "prompt_tps": next(p["avg_ts"] for p in pruebas if p["n_prompt"] > 0),
        "generacion_tps": next(p["avg_ts"] for p in pruebas if p["n_gen"] > 0),
    }


def corpus_en_texto() -> Path:
    docs = sorted((AQUI.parent / "03-rag" / "datos" / "docs").glob("*.md"))
    ruta = Path(tempfile.mkdtemp()) / "corpus.txt"
    ruta.write_text("\n\n".join(d.read_text(encoding="utf-8") for d in docs), encoding="utf-8")
    return ruta


def perplejidad(ruta: Path, texto: Path) -> float:
    from servidores import binario

    r = subprocess.run(
        [binario("llama-perplexity"), "-m", str(ruta), "-f", str(texto), "-c", "512"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    r.check_returncode()
    return float(re.search(r"Final estimate: PPL = ([\d.]+)", r.stdout + r.stderr)[1])


def evaluar(ruta: Path, nombre: str):
    import con_api
    import dataset
    from servidores import LlamaServer

    with LlamaServer(["-m", str(ruta), "-c", "4096"]):
        informe = con_api.ejecutar(ROL, dataset.cargar())
    informe.version = nombre
    informe.meta["modelo"] = ruta.name
    EVALS.mkdir(parents=True, exist_ok=True)
    informe.guardar(EVALS / f"{nombre}.jsonl")
    return informe


def medir() -> dict:
    import httpx
    from dotenv import load_dotenv

    load_dotenv()
    f16, origen = partida()
    niveles = cuantizar(f16)
    modelos = {"F16": {"ruta": str(f16), "bytes": f16.stat().st_size}} | niveles
    texto = corpus_en_texto()
    for nombre, m in modelos.items():
        m |= velocidad(Path(m["ruta"]))
        m["perplejidad"] = perplejidad(Path(m["ruta"]), texto)
        informe = evaluar(Path(m["ruta"]), nombre)
        m["latencia_p50_s"] = informe.meta["uso"]["latencia_p50_s"]
        m["ruta"] = Path(m["ruta"]).name  # la ruta completa es local
    etiquetas = httpx.get("http://127.0.0.1:11434/api/tags").json()["models"]
    return {
        "origen": origen,
        "modelos": modelos,
        "ollama_bytes": {m["name"]: m["size"] for m in etiquetas},
    }


def main() -> int:
    import dataset
    from curso_core import config as cfg
    from curso_core.evals import Informe, comparar, intervalo_wilson, prueba_mcnemar

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no descarga ni ejecuta")
    args = parser.parse_args()
    ruta = RESULTADOS / "cuantizar.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    # Las evals se repuntúan desde las respuestas grabadas, como en el módulo 4.
    por_id = {c.id: c for c in dataset.cargar()}

    def cargar(fichero: Path) -> Informe:
        informe = Informe.cargar(fichero)
        for res in informe.resultados:
            res.ok = dataset.puntuar(por_id[res.caso], res.salida)
        return informe

    evals = {n: cargar(EVALS / f"{n}.jsonl") for n in r["modelos"]}
    o, modelos = r["origen"], r["modelos"]
    print(f"1. Partida: {o['repo']}, {o['fichero']} (commit {o['commit'][:12]})")
    print(f"   {modelos['F16']['bytes'] / 1e9:.2f} GB")

    print("\n2. Cuantizado con llama-quantize")
    print(f"   {'':8} {'tamaño':>8} {'bits/peso':>10} {'tiempo':>7}   oficial de Qwen")
    for nombre, m in modelos.items():
        oficial = next(
            (b for f, b in o["oficiales"].items() if f.lower().endswith(f"{nombre.lower()}.gguf")),
            None,
        )
        bits = m.get("bpw", 16.0)  # el que informa llama-quantize
        tiempo = f"{m['segundos']:>6.0f}s" if "segundos" in m else f"{'':>7}"
        print(
            f"   {nombre:8} {m['bytes'] / 1e9:>6.2f}GB {bits:>10.2f} {tiempo}   "
            + (f"{oficial / 1e9:.2f} GB" if oficial else "")
        )
    print("   tipo de algunos tensores tras cuantizar:")
    for nombre in ("Q8_0", "Q4_K_M", "Q2_K"):
        tensores = ", ".join(
            f"{t.split('.')[-1]} {v}" for t, v in modelos[nombre]["tensores"].items()
        )
        print(f"      {nombre:7} {tensores}")

    print("\n3-4. Velocidad (llama-bench) y perplejidad sobre el corpus del asistente")
    print(f"   {'':8} {'prompt t/s':>11} {'generar t/s':>12} {'perplejidad':>12}")
    for nombre, m in modelos.items():
        print(
            f"   {nombre:8} {m['prompt_tps']:>11.0f} {m['generacion_tps']:>12.1f}"
            f" {m['perplejidad']:>12.2f}"
        )

    con = [c for c in por_id.values() if c.debe_responder]
    print("\n5. La eval del módulo 4: 58 preguntas, sistema vigente con cada modelo")
    print(
        f"   {'':8} {'aciertos':>9} {'IC 95 %':>10} {'se abstiene*':>13} {'p50':>6}"
        f" {'frente a F16':>18}"
    )
    base = evals["F16"]
    for nombre, m in modelos.items():
        e = evals[nombre]
        bajo, alto = intervalo_wilson(e.aciertos, e.total)
        c = comparar(base, e)
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        frente = "" if nombre == "F16" else f"+{len(c.ganados)} -{len(c.perdidos)} p={p:.2f}"
        salidas = e.por_caso()
        abstiene = sum(dataset.se_niega(salidas[c.id].salida) for c in con)
        print(
            f"   {nombre:8} {e.aciertos:>3} de {e.total} {bajo:>4.0%}-{alto:.0%}"
            f" {abstiene:>6} de {len(con)} {m['latencia_p50_s']:>5.1f}s {frente:>18}"
        )
    print(f"   * se abstiene en preguntas que sí tienen respuesta en la documentación ({len(con)})")

    print("\n   Referencias, grabadas en módulos anteriores:")
    vigente = cargar(MODULO_4 / "resultados" / "vigente.jsonl")
    respaldo = cargar(AQUI.parent / "06-produccion" / "resultados" / "respaldo-chat.jsonl")
    roles = cfg.cargar().roles
    for nombre, e, modelo in (
        ("1,5B en Ollama (lección 6.01)", respaldo, roles["chat"].model),
        ("7B en Ollama (sistema vigente)", vigente, roles["chat_grande"].model),
    ):
        tam = r["ollama_bytes"].get(modelo, 0) / 1e9
        print(f"   {nombre:32} {tam:.2f} GB  {e.aciertos} de {e.total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

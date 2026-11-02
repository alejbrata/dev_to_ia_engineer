"""Lección 7.03: el mismo modelo con tres servidores de inferencia locales.

El modelo de 1,5B del asistente, servido por:
- Ollama, con su versión Q4_K_M (la que usa el curso desde el módulo 1);
- llama.cpp (llama-server), con el GGUF Q4_K_M oficial de Qwen y 4 ranuras en paralelo;
- vLLM, con los pesos originales del Hub (los de la lección 02), en su imagen de Docker
  para CPU.

1. Una pregunta cada vez: tiempo hasta el primer token, velocidad y aciertos, en las
   mismas 8 preguntas del asistente con los fragmentos que recuperó el sistema vigente.
2. Cuatro preguntas a la vez: cuántos tokens por segundo saca cada servidor en total y
   cuánto espera cada petición.
3. Lo que reserva cada servidor al arrancar: el registro de vLLM sin límite de caché KV
   y el de llama-server con 8 ranuras en 4.096 tokens de contexto, frente al prompt del
   sistema vigente, con las dos formas de arreglarlo (--kv-unified y más contexto).

Necesita Ollama, llama.cpp (en el PATH o en LLAMA_CPP_DIR) y Docker con la imagen de
vLLM para CPU (unos 8 GB). Tarda más de una hora en la CPU del curso, sobre todo por el
arranque de vLLM. Con --grabadas, un segundo.
Uso: `uv run python modulos/07-modelos-propios/servir.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

import preparar

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
N = 8
CONCURRENCIA = 4
MAX_TOKENS = 150
# Lo que necesita vLLM en esta máquina: sin límite, reserva para la caché KV más memoria
# de la que tiene la máquina virtual de Docker (parte 3). --enforce-eager le ahorra compilar
# el modelo al arrancar: en la CPU del curso, compilando, no arrancó en 18 minutos.
KV_VLLM = 2 * 1024**3


def p95(valores: list[float]) -> float:
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, round(0.95 * (len(ordenados) - 1)))]


def una_peticion(rol: str, mensajes) -> dict:
    from curso_core import ClienteLLM, ErrorLLM, Opciones

    cliente = ClienteLLM(reintentos=0)
    t = time.perf_counter()
    try:
        flujo = cliente.chat_stream(
            mensajes, rol=rol, opciones=Opciones(temperatura=0, max_tokens=MAX_TOKENS)
        )
        texto = "".join(flujo)
    except ErrorLLM as e:
        return {"error": str(e)[:300], "segundos": time.perf_counter() - t}
    r = flujo.respuesta
    return {
        "texto": texto,
        "primer_token_s": r.primer_token_s,
        "segundos": time.perf_counter() - t,
        "tokens_entrada": r.tokens_entrada,
        "tokens_salida": r.tokens_salida,
    }


def medir_servidor(rol: str, preguntas) -> dict:
    """Primero de una en una (con una de calentamiento), después varias a la vez."""
    import dataset

    todos = {c.id: c for c in dataset.cargar()}
    una_peticion(rol, preguntas[0][1])
    secuencial = {caso: una_peticion(rol, m) for caso, m in preguntas}
    t = time.perf_counter()
    with ThreadPoolExecutor(CONCURRENCIA) as grupo:
        paralelo = list(grupo.map(lambda p: una_peticion(rol, p[1]), preguntas))
    pared = time.perf_counter() - t
    return {
        "secuencial": secuencial,
        "aciertos": sum(
            dataset.puntuar(todos[k], v.get("texto", "")) for k, v in secuencial.items()
        ),
        "paralelo": {"pared_s": pared, "peticiones": paralelo},
    }


def medir() -> dict:
    from curso_core import config as cfg
    from servidores import VLLM, LlamaServer

    config = cfg.cargar()
    preguntas = preparar.casos(N)
    grabado = json.loads((RESULTADOS / "preparar.json").read_text(encoding="utf-8"))
    commit = grabado["hub"]["commit"]
    gguf = config.roles["chat_llamacpp"].model
    hf = config.roles["chat_vllm"].model
    salida: dict = {"servidores": {}, "arranque": {}}

    salida["servidores"]["Ollama"] = medir_servidor("chat", preguntas)

    llama = ["-hf", gguf, "-c", "8192", "--parallel", str(CONCURRENCIA)]
    with LlamaServer(llama):
        salida["servidores"]["llama.cpp"] = medir_servidor("chat_llamacpp", preguntas)

    # vLLM, primero sin límite de caché KV: lo que hace por defecto.
    comunes = ["--revision", commit, "--max-model-len", "4096", "--enforce-eager"]
    sin_limite = VLLM(hf, comunes)
    t = time.perf_counter()
    try:
        with sin_limite:
            salida["arranque"]["vllm_sin_limite"] = {"error": None}
    except RuntimeError:
        registro = sin_limite.ultimo_registro
        salida["arranque"]["vllm_sin_limite"] = {
            "error": next((lin for lin in registro.splitlines() if "ValueError:" in lin), "").split(
                "ValueError: ", 1
            )[-1][:400],
            "segundos": time.perf_counter() - t,
        }
    vllm = VLLM(
        hf,
        [*comunes, "--kv-cache-memory-bytes", str(KV_VLLM)],
    )
    t = time.perf_counter()
    with vllm:
        salida["arranque"]["vllm_s"] = time.perf_counter() - t
        salida["servidores"]["vLLM"] = medir_servidor("chat_vllm", preguntas)
        registro = vllm.registro()
    salida["arranque"]["vllm_kv"] = [
        lin.split("] ", 1)[-1] for lin in registro.splitlines() if "KV cache" in lin
    ][:3]

    salida["arranque"] |= ranuras_llama(gguf)
    return salida


def ranuras_llama(gguf: str) -> dict:
    """llama-server con 8 ranuras en 4.096 tokens, con el prompt del sistema vigente, y las
    dos formas de arreglarlo: más contexto o una caché compartida entre ranuras."""
    from servidores import LlamaServer

    vigentes = preparar.casos(N, prompt="rag/con-citas-reglas")
    salida = {}
    for nombre, extra in (
        ("llama_8_ranuras", ["-c", "4096"]),
        ("con_kv_unified", ["-c", "4096", "--kv-unified"]),
        ("con_c_8192", ["-c", "8192"]),
    ):
        with LlamaServer(["-hf", gguf, *extra, "--parallel", "8"]) as servidor:
            with ThreadPoolExecutor(8) as grupo:
                respuestas = list(
                    grupo.map(lambda p: una_peticion("chat_llamacpp", p[1]), vigentes)
                )
            ranuras = re.search(r"n_slots = \d+, n_ctx_slot = \d+", servidor.leer_registro())
        salida[nombre] = {
            "argumentos": " ".join([*extra, "--parallel", "8"]),
            "ranuras": ranuras[0] if ranuras else "",
            "respuestas": respuestas,
        }
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no arranca nada")
    args = parser.parse_args()
    ruta = RESULTADOS / "servir.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"1. Una pregunta cada vez ({N} preguntas, máximo {MAX_TOKENS} tokens, voraz)")
    print(f"   {'':10} {'primer token':>13} {'tokens/s':>9} {'respuesta':>10} {'aciertos':>9}")
    for nombre, s in r["servidores"].items():
        v = [x for x in s["secuencial"].values() if "error" not in x]
        ttft = median(x["primer_token_s"] for x in v)
        tps = median(
            (x["tokens_salida"] - 1) / (x["segundos"] - x["primer_token_s"])
            for x in v
            if x["tokens_salida"] > 1
        )
        resp = median(x["segundos"] for x in v)
        print(f"   {nombre:10} {ttft:>12.2f}s {tps:>9.1f} {resp:>9.1f}s {s['aciertos']:>4} de {N}")
    print("   (medianas por petición; tokens/s: generación, sin contar el primer token)")

    print(f"\n2. {CONCURRENCIA} preguntas a la vez (las mismas {N})")
    print(f"   {'':10} {'tokens/s en total':>18} {'respuesta p50':>14} {'p95':>7} {'errores':>8}")
    for nombre, s in r["servidores"].items():
        p = s["paralelo"]
        ok = [x for x in p["peticiones"] if "error" not in x]
        total = sum(x["tokens_salida"] for x in ok) / p["pared_s"]
        tiempos = [x["segundos"] for x in ok]
        errores = len(p["peticiones"]) - len(ok)
        print(
            f"   {nombre:10} {total:>18.1f} {median(tiempos):>13.1f}s {p95(tiempos):>6.1f}s"
            f" {errores:>8}"
        )
    print("   frente a una cada vez (tokens/s en total = tokens/s de una petición):")
    for nombre, s in r["servidores"].items():
        v = [x for x in s["secuencial"].values() if "error" not in x]
        uno = sum(x["tokens_salida"] for x in v) / sum(x["segundos"] for x in v)
        p = s["paralelo"]
        total = sum(x.get("tokens_salida", 0) for x in p["peticiones"]) / p["pared_s"]
        print(f"   {nombre:10} {uno:>6.1f} → {total:>5.1f} ({total / uno:.1f}x)")

    a = r["arranque"]
    print("\n3. Lo que reserva cada servidor al arrancar")
    sin = a["vllm_sin_limite"]
    print(
        f"   vLLM sin límite de caché KV: falló a los {sin['segundos']:.0f} s"
        if sin["error"]
        else "   vLLM sin límite de caché KV: arrancó"
    )
    if sin["error"]:
        print(f"      {sin['error']}")
    print(f"   vLLM con --kv-cache-memory-bytes {KV_VLLM}: arrancó en {a['vllm_s'] / 60:.1f} min")
    for linea in a["vllm_kv"]:
        print(f"      {linea}")
    ll = a["llama_8_ranuras"]
    errores = [x for x in ll["respuestas"] if "error" in x]
    print(f"   llama-server -c 4096 --parallel 8: {ll['ranuras']}")
    print(f"      {N} preguntas con el prompt del sistema vigente: {len(errores)} con error")
    entradas = [x["tokens_entrada"] for x in ll["respuestas"] if "error" not in x]
    if entradas:
        print(f"      las que pasaron: {min(entradas)} a {max(entradas)} tokens de entrada")
    if errores:
        print(f"      {errores[0]['error'][:200]}")
    for clave in ("con_kv_unified", "con_c_8192"):
        x = a[clave]
        fallos = sum("error" in y for y in x["respuestas"])
        print(f"   llama-server {x['argumentos']}: {x['ranuras']}, {fallos} con error")
    return 0


if __name__ == "__main__":
    sys.exit(main())

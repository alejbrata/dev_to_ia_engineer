"""Lección 7.05 (1): los datos para ajustar el modelo de 1,5B con las respuestas del de 7B.

1. Preguntas sintéticas: el modelo de 7B escribe, por cada fragmento del corpus, dos
   preguntas que el fragmento responde y una que pide un dato que no está; y, aparte,
   preguntas fuera de ámbito e intentos de saltarse las instrucciones.
2. Filtro: fuera las que se parecen demasiado a alguna de las 58 preguntas de la eval
   (embeddings), para no entrenar con el examen, y las casi repetidas entre sí.
3. Respuestas del maestro: el sistema vigente (búsqueda con reranker, prompt con reglas
   y el modelo de 7B) responde cada pregunta. Su prompt y su respuesta son un ejemplo.
4. División en entrenamiento y validación.

Necesita Ollama con el modelo de 7B y los embeddings, y el reranker en llama-server.
Tarda algo más de una hora en la CPU del curso; con --grabadas, un segundo.
Uso: `uv run python modulos/07-modelos-propios/datos_ajuste.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

from curso_core import config as cfg
from pydantic import BaseModel

AQUI = Path(__file__).resolve().parent
RESULTADOS = cfg.carpeta_resultados(AQUI / "resultados" / "ajuste")
DATOS = RESULTADOS / "datos.jsonl"
MODULO_4 = AQUI.parent / "04-evals"
sys.path.insert(0, str(MODULO_4))
sys.path.insert(0, str(AQUI.parent / "03-rag"))
MAESTRO = "chat_grande"
# Parecido (coseno de los embeddings) a partir del cual una pregunta generada se descarta.
UMBRAL_EVAL = 0.85
UMBRAL_REPETIDA = 0.95
HILOS = 3
VALIDACION = 0.1


class Preguntas(BaseModel):
    con_respuesta: list[str]
    sin_respuesta: str


class Rechazables(BaseModel):
    fuera_de_ambito: list[str]
    manipulacion: list[str]


def generar(cliente) -> list[dict]:
    import sistema
    from curso_core import ErrorLLM, Opciones, prompts

    opciones = Opciones(temperatura=0.7, max_tokens=300)
    plantilla = prompts.cargar("modelos/generar-preguntas")

    def de_fragmento(f) -> list[dict]:
        mensajes = prompts.renderizar(plantilla, fragmento=f"{f.titulo}\n{f.texto}")
        try:
            p, _ = cliente.extraer(mensajes, Preguntas, rol=MAESTRO, opciones=opciones)
        except ErrorLLM:
            return []
        return [
            {"pregunta": q, "origen": f.id, "tipo": "con_respuesta"} for q in p.con_respuesta[:2]
        ] + [{"pregunta": p.sin_respuesta, "origen": f.id, "tipo": "sin_respuesta"}]

    with ThreadPoolExecutor(HILOS) as grupo:
        preguntas = [
            q for lista in grupo.map(de_fragmento, sistema.fragmentos().values()) for q in lista
        ]
    mensajes = prompts.renderizar(prompts.cargar("modelos/generar-fuera-de-ambito"), n="20")
    r, _ = cliente.extraer(
        mensajes, Rechazables, rol=MAESTRO, opciones=Opciones(temperatura=0.7, max_tokens=1500)
    )
    for tipo in ("fuera_de_ambito", "manipulacion"):
        preguntas += [{"pregunta": q, "origen": "", "tipo": tipo} for q in getattr(r, tipo)]
    return preguntas


def coseno(a: list[float], b: list[float]) -> float:
    import numpy as np

    va, vb = np.asarray(a), np.asarray(b)
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb)))


def filtrar(cliente, preguntas: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separa las preguntas que se pueden usar de las que se parecen a la eval o entre sí."""
    import dataset
    import numpy as np

    eval_ = [c.pregunta for c in dataset.cargar()]
    textos = [p["pregunta"] for p in preguntas]
    vectores = np.asarray(cliente.embeber(textos + eval_).vectores)
    vectores /= np.linalg.norm(vectores, axis=1, keepdims=True)
    gen, ev = vectores[: len(textos)], vectores[len(textos) :]
    con_eval = gen @ ev.T
    quedan, fuera, elegidos = [], [], []
    for i, p in enumerate(preguntas):
        j = int(con_eval[i].argmax())
        if con_eval[i, j] >= UMBRAL_EVAL:
            fuera.append(
                p | {"motivo": "eval", "parecida": eval_[j], "coseno": float(con_eval[i, j])}
            )
        elif elegidos and float((gen[elegidos] @ gen[i]).max()) >= UMBRAL_REPETIDA:
            fuera.append(p | {"motivo": "repetida"})
        else:
            elegidos.append(i)
            quedan.append(p)
    return quedan, fuera


def maestro(cliente, preguntas: list[dict]) -> list[dict]:
    """Las respuestas del sistema vigente, con el prompt exacto que recibió el modelo."""
    import evaluar
    import generacion
    import sistema
    from curso_core import ErrorFormato, prompts

    indice = sistema.indice(cliente, reranker=evaluar.SISTEMA["reranker"])
    plantilla = prompts.cargar(evaluar.SISTEMA["prompt"])

    def responder(p: dict) -> dict:
        resultados = indice.buscar(p["pregunta"], evaluar.SISTEMA["k"])
        mensajes = prompts.renderizar(
            plantilla, contexto=generacion.contexto(resultados), pregunta=p["pregunta"]
        )
        try:
            r, _ = cliente.extraer(
                mensajes, generacion.RespuestaCitada, rol=MAESTRO, opciones=generacion.OPCIONES
            )
            objetivo = json.dumps(r.model_dump(), ensure_ascii=False)
        except ErrorFormato:
            objetivo = None
        particion = (
            "validacion"
            if int(hashlib.sha256(p["pregunta"].encode()).hexdigest(), 16) % 100 < VALIDACION * 100
            else "entrenamiento"
        )
        return p | {
            "mensajes": [{"role": m.role, "content": m.content} for m in mensajes.mensajes],
            "objetivo": objetivo,
            "particion": particion,
        }

    with ThreadPoolExecutor(HILOS) as grupo:
        return list(grupo.map(responder, preguntas))


def medir() -> dict:
    from curso_core import ClienteLLM
    from dotenv import load_dotenv

    load_dotenv()
    cliente = ClienteLLM()
    t = time.perf_counter()
    preguntas = generar(cliente)
    t_generar = time.perf_counter() - t
    quedan, fuera = filtrar(cliente, preguntas)
    t = time.perf_counter()
    ejemplos = maestro(cliente, quedan)
    t_maestro = time.perf_counter() - t
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    with DATOS.open("w", encoding="utf-8") as f:
        for e in ejemplos:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return {
        "generadas": len(preguntas),
        "descartadas": fuera,
        "segundos_generar": t_generar,
        "segundos_maestro": t_maestro,
    }


def main() -> int:
    from collections import Counter

    import dataset
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a ningún modelo")
    args = parser.parse_args()
    ruta = RESULTADOS / "datos.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir()
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    ejemplos = [json.loads(linea) for linea in DATOS.read_text(encoding="utf-8").splitlines()]

    tipos = Counter(e["tipo"] for e in ejemplos) + Counter(d["tipo"] for d in r["descartadas"])
    print(
        f"1. Preguntas generadas por el modelo de 7B: {r['generadas']},"
        f" en {r['segundos_generar'] / 60:.0f} min"
    )
    for tipo, n in tipos.items():
        print(f"   {tipo:16} {n:>4}")

    motivos = Counter(d["motivo"] for d in r["descartadas"])
    print(f"\n2. Descartadas: {motivos['eval']} por parecerse a la eval (coseno ≥ {UMBRAL_EVAL}),")
    print(f"   {motivos['repetida']} casi repetidas (≥ {UMBRAL_REPETIDA})")
    for d in sorted(
        (d for d in r["descartadas"] if d["motivo"] == "eval"), key=lambda d: -d["coseno"]
    )[:4]:
        print(f"   {d['coseno']:.2f}  generada: {d['pregunta']}")
        print(f"         eval:     {d['parecida']}")

    validos = [e for e in ejemplos if e["objetivo"]]
    print(
        "\n3. Respuestas del maestro (sistema vigente con el 7B),"
        f" en {r['segundos_maestro'] / 60:.0f} min"
    )
    print(f"   {len(validos)} de {len(ejemplos)} con JSON válido")
    print(f"   {'':16} {'ejemplos':>9} {'se abstiene':>12}")
    for tipo in tipos:
        de_tipo = [e for e in validos if e["tipo"] == tipo]
        abst = sum(dataset.se_niega(json.loads(e["objetivo"])["respuesta"]) for e in de_tipo)
        print(f"   {tipo:16} {len(de_tipo):>9} {abst:>7} ({abst / max(len(de_tipo), 1):.0%})")

    tk = AutoTokenizer.from_pretrained(cfg.cargar().roles["chat"].hf_repo)
    entrada = [
        len(tk.apply_chat_template(e["mensajes"], add_generation_prompt=True)["input_ids"])
        for e in validos
    ]
    salida = [len(tk(e["objetivo"]).input_ids) for e in validos]
    particiones = Counter(e["particion"] for e in validos)
    print(
        f"\n4. {particiones['entrenamiento']} de entrenamiento"
        f" y {particiones['validacion']} de validación"
    )
    print(
        f"   tokens por ejemplo (mediana): {median(entrada):.0f} de prompt"
        f" y {median(salida):.0f} de respuesta"
    )
    e = next(e for e in validos if e["tipo"] == "sin_respuesta")
    print(f"   un ejemplo ({e['tipo']}): «{e['pregunta']}»")
    print(f"      → {e['objetivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

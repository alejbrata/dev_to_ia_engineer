"""Anexo B.2: encoder, encoder-decoder y decoder, con transformers y los mismos textos.

1. Los tres modelos: su arquitectura, su clase de transformers, su tamaño y cuánto tardan
   en cargar.
2. Cada uno en lo suyo, sobre cinco tickets del módulo 2: el encoder clasifica el tono, el
   encoder-decoder traduce al inglés y el decoder resume en una frase.
3. El decoder haciendo lo del encoder-decoder (traducir): sí puede, ¿a qué precio?

Usa la CPU. La primera vez descarga unos 1,4 GB. Necesita `uv sync --group hf`.
Con --grabadas no carga ningún modelo.
Uso: `uv run python modulos/b-hugging-face/arquitecturas.py [--grabadas]`
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
TICKETS = AQUI.parent / "02-prompting" / "datos" / "tickets.jsonl"
N = 5
MODELOS = {
    "encoder": "UMUTeam/roberta-spanish-sentiment-analysis",
    "encoder-decoder": "Helsinki-NLP/opus-mt-es-en",
    "decoder": "Qwen/Qwen2.5-0.5B-Instruct",
}


def textos() -> list[str]:
    lineas = TICKETS.read_text(encoding="utf-8").splitlines()
    return [json.loads(linea)["texto"] for linea in lineas[:N]]


def parametros(modelo) -> int:
    return sum(p.numel() for p in modelo.parameters())


def cronometrar(funcion, entradas: list[str]) -> tuple[list[str], list[float]]:
    salidas, segundos = [], []
    for x in entradas:
        inicio = time.perf_counter()
        salidas.append(funcion(x))
        segundos.append(time.perf_counter() - inicio)
    return salidas, segundos


def medir() -> dict:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoModelForSeq2SeqLM,
        AutoModelForSequenceClassification,
        AutoTokenizer,
    )

    torch.manual_seed(0)
    entradas = textos()
    modelos, tokenizers, carga = {}, {}, {}
    clases = {
        "encoder": AutoModelForSequenceClassification,
        "encoder-decoder": AutoModelForSeq2SeqLM,
        "decoder": AutoModelForCausalLM,
    }
    for tipo, nombre in MODELOS.items():
        inicio = time.perf_counter()
        tokenizers[tipo] = AutoTokenizer.from_pretrained(nombre)
        modelos[tipo] = clases[tipo].from_pretrained(nombre).eval()
        carga[tipo] = time.perf_counter() - inicio

    @torch.no_grad()
    def clasificar(texto: str) -> str:
        m, t = modelos["encoder"], tokenizers["encoder"]
        probabilidades = m(**t(texto, return_tensors="pt")).logits.softmax(-1)[0]
        clase = int(probabilidades.argmax())
        return f"{m.config.id2label[clase]} ({probabilidades[clase]:.2f})"

    @torch.no_grad()
    def traducir(texto: str) -> str:
        m, t = modelos["encoder-decoder"], tokenizers["encoder-decoder"]
        salida = m.generate(**t(texto, return_tensors="pt"), max_new_tokens=120)
        return t.decode(salida[0], skip_special_tokens=True)

    @torch.no_grad()
    def generar(instruccion: str, texto: str) -> str:
        m, t = modelos["decoder"], tokenizers["decoder"]
        mensajes = [{"role": "user", "content": f"{instruccion}\n\n{texto}"}]
        prompt = t.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
        ids = t(prompt, return_tensors="pt")
        salida = m.generate(**ids, max_new_tokens=120, do_sample=False)
        return t.decode(salida[0][ids["input_ids"].shape[1] :], skip_special_tokens=True).strip()

    tareas = {
        "encoder": clasificar,
        "encoder-decoder": traducir,
        "decoder": lambda x: generar("Resume este ticket en una frase corta.", x),
        "decoder traduciendo": lambda x: generar("Traduce al inglés este texto:", x),
    }
    resultado = {
        "textos": entradas,
        "modelos": {
            tipo: {
                "nombre": MODELOS[tipo],
                "clase": type(modelos[tipo]).__name__,
                "parametros": parametros(modelos[tipo]),
                "carga_s": round(carga[tipo], 1),
            }
            for tipo in MODELOS
        },
        "tareas": {},
    }
    for tarea, funcion in tareas.items():
        salidas, segundos = cronometrar(funcion, entradas)
        segundos = [round(s, 2) for s in segundos]
        resultado["tareas"][tarea] = {"salidas": salidas, "segundos": segundos}
    return resultado


def media(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no carga ningún modelo")
    args = parser.parse_args()
    load_dotenv()  # HF_TOKEN, si está (opcional)
    ruta = RESULTADOS / "arquitecturas.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print("1. Los tres modelos")
    print(f"   {'arquitectura':16} {'clase de transformers':36} {'parámetros':>10} {'carga':>6}")
    for tipo, m in r["modelos"].items():
        millones = f"{m['parametros'] / 1e6:.0f} M"
        print(f"   {tipo:16} {m['clase']:36} {millones:>10} {m['carga_s']:>5} s")
        print(f"   {'':16} {m['nombre']}")

    t = r["tareas"]
    print(f"\n2. Cada uno en lo suyo, en {len(r['textos'])} tickets")
    for i, texto in enumerate(r["textos"][:2]):
        print(f"   ticket: {texto[:96]}")
        print(f"     encoder (tono):           {t['encoder']['salidas'][i]}")
        print(f"     encoder-decoder (inglés): {t['encoder-decoder']['salidas'][i][:96]}")
        print(f"     decoder (resumen):        {t['decoder']['salidas'][i][:96]}")
    print(f"   {'':26} {'s por ticket (media)':>21}")
    for tarea in ("encoder", "encoder-decoder", "decoder"):
        print(f"   {tarea:26} {media(t[tarea]['segundos']):>21.2f}")

    print("\n3. El decoder traduciendo, frente al encoder-decoder")
    for i in range(2):
        print(f"   encoder-decoder: {t['encoder-decoder']['salidas'][i][:100]}")
        print(f"   decoder:         {t['decoder traduciendo']['salidas'][i][:100]}")
    ed, d = media(t["encoder-decoder"]["segundos"]), media(t["decoder traduciendo"]["segundos"])
    p_ed = r["modelos"]["encoder-decoder"]["parametros"]
    p_d = r["modelos"]["decoder"]["parametros"]
    print(f"   s por ticket: {ed:.2f} frente a {d:.2f} ({d / ed:.1f} veces más)")
    veces = p_d / p_ed
    print(f"   parámetros:   {p_ed / 1e6:.0f} M frente a {p_d / 1e6:.0f} M ({veces:.1f} veces más)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

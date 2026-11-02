"""Lección 7.05 (2): ajustar el modelo de 1,5B con LoRA, con las respuestas del de 7B.

1. El modelo base (los safetensors de la lección 02, con el commit fijado) en float32, con
   adaptadores LoRA en todas sus matrices lineales: cuántos parámetros se entrenan.
2. El entrenamiento: dos épocas sobre los ejemplos de datos_ajuste.py, con la pérdida
   solo sobre los tokens de la respuesta. La pérdida de validación se mide cada media
   época, para ver si aprende o memoriza.
3. Lo que queda: un adaptador por época (unos MB) y, para servirlo, el modelo con el
   adaptador fusionado.

Necesita el grupo opcional `hf` y los datos de datos_ajuste.py. Es CPU pura: unas cuatro
horas y media en la máquina del curso. Los modelos van a ~/.cache/curso-ai-engineer/lora.
Con --grabadas, un segundo.
Uso: `uv run --group hf python modulos/07-modelos-propios/ajustar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados" / "ajuste"
# Los datos de datos_ajuste.py, o los de corregir_datos.py (lección 06): fichero de datos y
# sufijo de los adaptadores, los modelos fusionados y los resultados.
VARIANTES = {
    "original": ("datos.jsonl", ""),
    "corregidos": ("datos-corregidos.jsonl", "-corregido"),
}
TRABAJO = Path.home() / ".cache" / "curso-ai-engineer" / "lora"
EPOCAS = 2
ACUMULAR = 8  # ejemplos por paso del optimizador (lotes de uno, gradientes acumulados)
LR = 2e-4
LORA = {
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj",
    ],
}  # fmt: skip
VALIDACIONES_POR_EPOCA = 2


def base() -> str:
    """La carpeta del modelo base: el del rol chat, en el commit grabado en la lección 02."""
    from curso_core import config as cfg
    from huggingface_hub import snapshot_download

    commit = json.loads((AQUI / "resultados" / "preparar.json").read_text(encoding="utf-8"))
    repo = cfg.cargar().roles["chat"].hf_repo
    patrones = ["*.safetensors", "*.json", "merges.txt", "vocab.json"]
    return snapshot_download(repo, revision=commit["hub"]["commit"], allow_patterns=patrones)


def ejemplos(tokenizador, variante: str = "original") -> dict[str, list[dict]]:
    """Cada ejemplo, tokenizado con la plantilla de chat; las etiquetas del prompt van a
    -100 para que la pérdida cuente solo la respuesta."""
    salida: dict[str, list[dict]] = {"entrenamiento": [], "validacion": []}
    fichero = RESULTADOS / VARIANTES[variante][0]
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        e = json.loads(linea)
        if not e["objetivo"]:
            continue
        prompt = tokenizador.apply_chat_template(e["mensajes"], add_generation_prompt=True)[
            "input_ids"
        ]
        # El ejemplo completo termina en <|im_end|>: el modelo aprende también a parar.
        completo = tokenizador.apply_chat_template(
            [*e["mensajes"], {"role": "assistant", "content": e["objetivo"]}]
        )["input_ids"]
        if completo[: len(prompt)] != prompt:
            raise ValueError("La plantilla no deja el prompt como prefijo del ejemplo completo")
        etiquetas = [-100] * len(prompt) + completo[len(prompt) :]
        salida[e["particion"]].append({"ids": completo, "etiquetas": etiquetas})
    return salida


def perdida(modelo, conjunto: list[dict]) -> float:
    import torch

    modelo.eval()
    total, n = 0.0, 0
    with torch.no_grad():
        for e in conjunto:
            out = modelo(input_ids=torch.tensor([e["ids"]]), labels=torch.tensor([e["etiquetas"]]))
            tokens = sum(t != -100 for t in e["etiquetas"])
            total += out.loss.item() * tokens
            n += tokens
    modelo.train()
    return total / n


def entrenar(variante: str = "original") -> dict:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(0)
    ruta = base()
    tokenizador = AutoTokenizer.from_pretrained(ruta)
    datos = ejemplos(tokenizador, variante)
    sufijo = VARIANTES[variante][1]
    modelo = AutoModelForCausalLM.from_pretrained(ruta, dtype=torch.float32)
    modelo = get_peft_model(modelo, LoraConfig(task_type="CAUSAL_LM", **LORA))
    entrenables = sum(p.numel() for p in modelo.parameters() if p.requires_grad)
    totales = sum(p.numel() for p in modelo.parameters())
    optimizador = torch.optim.AdamW([p for p in modelo.parameters() if p.requires_grad], lr=LR)
    pasos_totales = EPOCAS * len(datos["entrenamiento"]) // ACUMULAR
    planificador = torch.optim.lr_scheduler.LambdaLR(
        optimizador, lambda paso: max(0.0, 1 - paso / pasos_totales)
    )

    curva = [{"epoca": 0.0, "validacion": perdida(modelo, datos["validacion"])}]
    print(curva[-1], flush=True)
    orden = random.Random(0)
    n = len(datos["entrenamiento"])
    cada = n // VALIDACIONES_POR_EPOCA
    inicio = time.perf_counter()
    modelo.train()
    for epoca in range(EPOCAS):
        indices = list(range(n))
        orden.shuffle(indices)
        acumulada, vistos = 0.0, 0
        for i, j in enumerate(indices, 1):
            e = datos["entrenamiento"][j]
            out = modelo(input_ids=torch.tensor([e["ids"]]), labels=torch.tensor([e["etiquetas"]]))
            (out.loss / ACUMULAR).backward()
            acumulada += out.loss.item()
            vistos += 1
            if i % ACUMULAR == 0 or i == n:
                optimizador.step()
                planificador.step()
                optimizador.zero_grad()
            if i % cada == 0 or i == n:
                curva.append(
                    {
                        "epoca": round(epoca + i / n, 2),
                        "entrenamiento": acumulada / vistos,
                        "validacion": perdida(modelo, datos["validacion"]),
                        "minutos": (time.perf_counter() - inicio) / 60,
                    }
                )
                acumulada, vistos = 0.0, 0
                print(curva[-1], flush=True)
        destino = TRABAJO / f"adaptador{sufijo}-epoca-{epoca + 1}"
        modelo.save_pretrained(destino)
    return {
        "entrenables": entrenables,
        "totales": totales,
        "ejemplos": {k: len(v) for k, v in datos.items()},
        "pasos": pasos_totales,
        "curva": curva,
        "minutos": (time.perf_counter() - inicio) / 60,
        "adaptador_bytes": sum(
            f.stat().st_size for f in (TRABAJO / f"adaptador{sufijo}-epoca-1").iterdir()
        ),
    }


def fusionar(variante: str = "original") -> dict:
    """El modelo base con cada adaptador fusionado, en bfloat16 como el original, para
    servirlo con cualquier servidor que lea safetensors (vLLM, en la lección 06)."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    ruta = base()
    sufijo = VARIANTES[variante][1]
    tamanos = {}
    for epoca in range(1, EPOCAS + 1):
        modelo = AutoModelForCausalLM.from_pretrained(ruta, dtype=torch.float32)
        modelo = PeftModel.from_pretrained(modelo, TRABAJO / f"adaptador{sufijo}-epoca-{epoca}")
        fusionado = modelo.merge_and_unload().to(torch.bfloat16)
        destino = TRABAJO / f"fusionado{sufijo}-epoca-{epoca}"
        fusionado.save_pretrained(destino)
        AutoTokenizer.from_pretrained(ruta).save_pretrained(destino)
        tamanos[str(epoca)] = sum(f.stat().st_size for f in destino.iterdir())
    return tamanos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no entrena")
    parser.add_argument("--datos", choices=VARIANTES, default="original")
    args = parser.parse_args()
    ruta = RESULTADOS / f"ajuste{VARIANTES[args.datos][1]}.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = entrenar(args.datos)
        # Se guarda antes de fusionar: si la fusión falla, no se pierden horas de entrenamiento.
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        r["fusionado_bytes"] = fusionar(args.datos)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print("1. LoRA sobre el modelo de 1,5B")
    print(
        f"   rango {LORA['r']}, alfa {LORA['lora_alpha']}, en {', '.join(LORA['target_modules'])}"
    )
    print(
        f"   parámetros que se entrenan: {r['entrenables']:,} de {r['totales']:,}"
        f" ({r['entrenables'] / r['totales']:.2%})"
    )
    ej = r["ejemplos"]
    print(
        f"\n2. Entrenamiento: {ej['entrenamiento']} ejemplos, {EPOCAS} épocas, {r['pasos']} pasos"
        f" de {ACUMULAR} ejemplos, en {r['minutos']:.0f} min"
    )
    print(f"   validación: {ej['validacion']} ejemplos")
    print(
        f"   {'época':>6} {'pérdida entrenamiento':>22} {'pérdida validación':>19} {'minutos':>8}"
    )
    for punto in r["curva"]:
        ent = f"{punto['entrenamiento']:.3f}" if "entrenamiento" in punto else "-"
        mins = f"{punto['minutos']:.0f}" if "minutos" in punto else "-"
        print(f"   {punto['epoca']:>6.1f} {ent:>22} {punto['validacion']:>19.3f} {mins:>8}")

    fusion = r["fusionado_bytes"]
    print("\n3. Lo que queda")
    print(f"   adaptador LoRA de una época: {r['adaptador_bytes'] / 1e6:.0f} MB")
    print(f"   modelo con el adaptador fusionado, en bfloat16: {fusion['1'] / 1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

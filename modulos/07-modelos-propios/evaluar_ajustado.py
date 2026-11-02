"""Lección 7.06: el modelo ajustado frente al base y frente al maestro, con la eval del módulo 4.

Los tres modelos de 1,5B (el base y el ajustado tras una y dos épocas) se sirven igual:
vLLM, la misma precisión y el mismo sistema vigente (búsqueda con reranker, prompt con
reglas y citas). Solo cambian los pesos.
1. Aciertos en las 58 preguntas, con su intervalo, y la comparación caso a caso con el
   base (McNemar); y el de 7B, el maestro, como techo.
2. Por tipo de pregunta: dónde gana y dónde pierde el ajustado.
3. Los 12 casos que en la lección 01 acertaba el 7B y fallaba el 1,5B: cuáles arregla.
4. Lo que cuesta cada uno: tiempo por respuesta.

Necesita Docker con la imagen de vLLM para CPU (lección 03), los modelos fusionados de
ajustar.py, Ollama con los embeddings y el reranker en llama-server. Unos 60 minutos
en la CPU del curso; con --grabadas, un segundo.
Uso: `uv run python modulos/07-modelos-propios/evaluar_ajustado.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados" / "ajuste"
MODULO_4 = AQUI.parent / "04-evals"
sys.path.insert(0, str(MODULO_4))
ROL = "chat_vllm"
TRABAJO = Path.home() / ".cache" / "curso-ai-engineer" / "lora"
KV = str(2 * 1024**3)


def evaluar(nombre: str, modelo: str, extra: list[str]) -> None:
    import con_api
    import dataset
    from curso_core import config as cfg
    from servidores import VLLM

    servido = cfg.cargar().roles[ROL].model
    argumentos = [
        *extra,
        "--served-model-name", servido,  # el nombre que pide el rol, sea cual sea el modelo
        "--max-model-len", "4096", "--enforce-eager", "--kv-cache-memory-bytes", KV,
    ]  # fmt: skip
    with VLLM(modelo, argumentos, carpeta=TRABAJO):
        informe = con_api.ejecutar(ROL, dataset.cargar())
    informe.version = nombre
    informe.meta["modelo"] = nombre
    informe.guardar(RESULTADOS / f"eval-{nombre}.jsonl")


def medir(corregidos: bool) -> None:
    from dotenv import load_dotenv

    load_dotenv()
    commit = json.loads((AQUI / "resultados" / "preparar.json").read_text(encoding="utf-8"))
    from curso_core import config as cfg

    if corregidos:  # solo los ajustados con los datos de corregir_datos.py
        for epoca in (1, 2):
            evaluar(f"corregido-epoca-{epoca}", f"/modelos/fusionado-corregido-epoca-{epoca}", [])
        return
    repo = cfg.cargar().roles["chat"].hf_repo
    evaluar("base", repo, ["--revision", commit["hub"]["commit"]])
    for epoca in (1, 2):
        evaluar(f"ajustado-epoca-{epoca}", f"/modelos/fusionado-epoca-{epoca}", [])


def main() -> int:
    from collections import Counter

    import dataset
    from curso_core.evals import Informe, comparar, intervalo_wilson, prueba_mcnemar

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no arranca nada")
    parser.add_argument(
        "--corregidos", action="store_true", help="evalúa solo los ajustados con datos corregidos"
    )
    args = parser.parse_args()
    if not args.grabadas:
        medir(args.corregidos)

    casos = dataset.cargar()
    por_id = {c.id: c for c in casos}

    def cargar(ruta: Path) -> Informe:
        informe = Informe.cargar(ruta)
        for res in informe.resultados:
            res.ok = dataset.puntuar(por_id[res.caso], res.salida)
        return informe

    # Los corregidos (lección 06, segunda parte), si ya se han evaluado.
    nombres = ["base", "ajustado-epoca-1", "ajustado-epoca-2"] + [
        n
        for n in ("corregido-epoca-1", "corregido-epoca-2")
        if (RESULTADOS / f"eval-{n}.jsonl").exists()
    ]
    modelos = {n: cargar(RESULTADOS / f"eval-{n}.jsonl") for n in nombres}
    modelos["maestro (7B)"] = cargar(MODULO_4 / "resultados" / "vigente.jsonl")
    base = modelos["base"]

    print("1. La eval del módulo 4 (58 preguntas), sistema vigente con cada modelo")
    print(f"   {'':18} {'aciertos':>9} {'IC 95 %':>10} {'frente al base':>20}")
    for nombre, e in modelos.items():
        bajo, alto = intervalo_wilson(e.aciertos, e.total)
        c = comparar(base, e)
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        frente = "" if nombre == "base" else f"+{len(c.ganados)} -{len(c.perdidos)} p={p:.2f}"
        print(f"   {nombre:18} {e.aciertos:>3} de {e.total} {bajo:>4.0%}-{alto:.0%} {frente:>20}")

    tipos = Counter(c.tipo for c in casos)
    print("\n2. Aciertos por tipo de pregunta")
    print(f"   {'':18}" + "".join(f"{t:>16}" for t in tipos))
    for nombre, e in modelos.items():
        res = e.por_caso()
        fila = "".join(
            f"{sum(res[c.id].ok for c in casos if c.tipo == t):>10} de {n:<3}"
            for t, n in tipos.items()
        )
        print(f"   {nombre:18}{fila}")
    con = [c for c in casos if c.debe_responder]
    print(f"   se abstiene en preguntas con respuesta ({len(con)}):")
    for nombre, e in modelos.items():
        res = e.por_caso()
        print(f"      {nombre:18} {sum(dataset.se_niega(res[c.id].salida) for c in con):>3}")

    # Los casos de la lección 01: los acierta el 7B y los falla el 1,5B de Ollama (6.01).
    respaldo = cargar(AQUI.parent / "06-produccion" / "resultados" / "respaldo-chat.jsonl")
    maestro, pequeno = modelos["maestro (7B)"].por_caso(), respaldo.por_caso()
    fallos_701 = [k for k in maestro if maestro[k].ok and not pequeno[k].ok]
    print(f"\n3. Los {len(fallos_701)} casos de la lección 01 (los acierta el 7B y no el 1,5B)")
    for nombre in nombres:
        res = modelos[nombre].por_caso()
        bien = [k for k in fallos_701 if res[k].ok]
        print(f"   {nombre:18} acierta {len(bien):>2}: {', '.join(bien)}")

    print("\n4. Tiempo por respuesta (mediana, con el servidor de cada uno)")
    for nombre, e in modelos.items():
        uso = e.meta.get("uso", {})
        if uso:
            print(f"   {nombre:18} {uso['latencia_p50_s']:>5.1f} s")
    print("   (los de 1,5B, en vLLM sobre CPU; el de 7B, en Ollama: módulo 4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

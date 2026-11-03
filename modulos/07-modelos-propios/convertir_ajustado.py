"""Lección 7.06 (3): el modelo ajustado servido como el base de la lección 04.

1. Convierte a GGUF en 16 bits el modelo fusionado de la lección 05 (safetensors), con
   el `convert_hf_to_gguf.py` de llama.cpp del mismo commit que tus binarios.
2. Lo cuantiza a Q4_K_M con `llama-quantize`, como el base de la lección 04.
3. Mide su velocidad con `llama-bench` y pasa la eval del módulo 4 servido con
   llama-server, para compararlo con el base Q4_K_M grabado en la lección 04.

El conversor tiene sus propias dependencias fijadas (otra versión de torch y de
transformers que el curso), así que va en un entorno aparte: la carpeta de
`CONVERTIR_GGUF_DIR` (por defecto `~/.cache/curso-ai-engineer/convertir`) con
`convert_hf_to_gguf.py`, `conversion/`, `gguf-py/` y un `.venv` con
`requirements/requirements-convert_hf_to_gguf.txt` instalado.

Necesita además llama.cpp (lección 03), Ollama con los embeddings y el reranker en
llama-server. Unos 15 minutos; con --grabadas, un segundo.
Uso: `uv run python modulos/07-modelos-propios/convertir_ajustado.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados" / "ajuste"
sys.path.insert(0, str(AQUI.parent / "04-evals"))
LORA = Path.home() / ".cache" / "curso-ai-engineer" / "lora"
GGUF = Path.home() / ".cache" / "curso-ai-engineer" / "gguf"
CONVERTIR = Path(
    os.environ.get("CONVERTIR_GGUF_DIR", Path.home() / ".cache" / "curso-ai-engineer" / "convertir")
)
# Nombre en la lección: carpeta del modelo fusionado (lección 05 y su versión corregida).
# El base se convierte también, con el mismo conversor: así solo cambian los pesos. El GGUF
# oficial de Qwen de la lección 04 se convirtió de otra forma (ver la lección 06).
TOKENIZADOR = ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")
MODELOS = {
    "base": None,
    "ajustado-epoca-2": "fusionado-epoca-2",
    "corregido-epoca-2": "fusionado-corregido-epoca-2",
}


def convertir(origen: Path, destino: Path) -> float:
    python = CONVERTIR / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    t = time.perf_counter()
    # Sin -I: el conversor importa su paquete `conversion/`, que está junto al script.
    r = subprocess.run(
        [str(python), str(CONVERTIR / "convert_hf_to_gguf.py"), str(origen)]
        + ["--outfile", str(destino), "--outtype", "f16"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"convert_hf_to_gguf.py falló:\n{r.stderr[-2000:]}")
    return time.perf_counter() - t


def copia_del_base(snapshot: Path) -> Path:
    """Los ficheros del modelo base en una carpeta normal. La caché del Hub, en Windows, puede
    tener enlaces a los que no se puede acceder (el README.md), y el conversor recorre la
    carpeta entera."""
    import shutil

    destino = LORA / "base"
    destino.mkdir(parents=True, exist_ok=True)
    for nombre in ("config.json", "generation_config.json", "model.safetensors", *TOKENIZADOR):
        shutil.copy(snapshot / nombre, destino / nombre)
    return destino


def medir(solo: str | None) -> dict:
    import ajustar
    import cuantizar
    from servidores import binario

    salida = {}
    for nombre, carpeta in MODELOS.items():
        if solo and nombre != solo:
            continue
        origen = copia_del_base(Path(ajustar.base())) if carpeta is None else LORA / carpeta
        if not origen.exists():
            print(f"   {nombre}: no existe {origen}, se salta", file=sys.stderr)
            continue
        GGUF.mkdir(parents=True, exist_ok=True)
        f16 = GGUF / f"{nombre}-f16.gguf"
        q4 = GGUF / f"{nombre}-Q4_K_M.gguf"
        # Los primeros modelos fusionados guardaron el tokenizador con transformers 5, que
        # el conversor no lee: se pone el original, que LoRA no cambia.
        if carpeta is not None:
            ajustar.copiar_tokenizador(Path(ajustar.base()), origen)
        conversion_s = convertir(origen, f16)
        subprocess.run(
            [binario("llama-quantize"), str(f16), str(q4), "Q4_K_M"],
            capture_output=True,
            check=True,
        )
        informe = cuantizar.evaluar(q4, f"ajuste-{nombre}-Q4_K_M")
        salida[nombre] = {
            "conversion_s": conversion_s,
            "f16_bytes": f16.stat().st_size,
            "q4_bytes": q4.stat().st_size,
            **cuantizar.velocidad(q4),
            "aciertos": informe.aciertos,
            "total": informe.total,
            "p50_s": informe.meta["uso"]["latencia_p50_s"],
        }
    return salida


def main() -> int:
    import dataset
    from curso_core.evals import Informe, comparar, intervalo_wilson, prueba_mcnemar

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no convierte ni mide")
    parser.add_argument("--solo", choices=MODELOS, help="convierte y mide solo este modelo")
    args = parser.parse_args()
    ruta = RESULTADOS / "convertir.json"
    r = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    if not args.grabadas:
        from dotenv import load_dotenv

        load_dotenv()
        r |= medir(args.solo)
        r = {n: r[n] for n in MODELOS if n in r}
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    por_id = {c.id: c for c in dataset.cargar()}

    def cargar(nombre: str) -> Informe:
        informe = Informe.cargar(AQUI / "resultados" / "cuantizar" / f"{nombre}.jsonl")
        for res in informe.resultados:
            res.ok = dataset.puntuar(por_id[res.caso], res.salida)
        return informe

    cuantizado = json.loads((AQUI / "resultados" / "cuantizar.json").read_text(encoding="utf-8"))
    base_q4 = cuantizado["modelos"]["Q4_K_M"]
    oficial = cargar("Q4_K_M")
    base = cargar("ajuste-base-Q4_K_M") if "base" in r else oficial
    print("1. Del modelo fusionado (safetensors) a GGUF en 16 bits y a Q4_K_M")
    for nombre, m in r.items():
        f16, q4 = m["f16_bytes"] / 1e9, m["q4_bytes"] / 1e9
        print(
            f"   {nombre:18} conversión {m['conversion_s']:.0f} s"
            f" · F16 {f16:.2f} GB · Q4_K_M {q4:.2f} GB"
        )
    print("\n2. Q4_K_M servido con llama.cpp, frente al base convertido igual")
    print(
        f"   {'':18} {'generar t/s':>11} {'aciertos':>9} {'IC 95 %':>10} {'p50':>6}"
        f" {'frente al base':>18}"
    )
    bajo, alto = intervalo_wilson(oficial.aciertos, oficial.total)
    tps, p50 = base_q4["generacion_tps"], base_q4["latencia_p50_s"]
    print(
        f"   {'oficial (lec. 04)':18} {tps:>11.1f} {oficial.aciertos:>3} de 58"
        f" {bajo:>4.0%}-{alto:.0%} {p50:>5.1f}s"
    )
    for nombre, m in r.items():
        e = cargar(f"ajuste-{nombre}-Q4_K_M")
        c = comparar(base, e)
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        bajo, alto = intervalo_wilson(e.aciertos, e.total)
        print(
            f"   {nombre:18} {m['generacion_tps']:>11.1f} {e.aciertos:>3} de 58"
            f" {bajo:>4.0%}-{alto:.0%} {m['p50_s']:>5.1f}s"
            + (
                ""
                if nombre == "base"
                else f" {f'+{len(c.ganados)} -{len(c.perdidos)} p={p:.2f}':>18}"
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

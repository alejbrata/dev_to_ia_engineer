"""Anexo B.3: laboratorio de clasificación de sentimiento, ¿encoder, LLM o embeddings?

Sobre los 870 tuits en español de test (290 de cada clase), compara:
- tres encoders ya ajustados para sentimiento, del Hub, con `pipeline` de transformers;
- un LLM sin ejemplos, con salida estructurada: el local del curso (rol `agente`) y, si
  se pide con --llm, otro rol (por ejemplo `chat_hf`, el Qwen3 de 235B de Hugging Face);
- embeddings (bge-m3, el del módulo 3) y una regresión logística entrenada con los 1839
  tuits de train.

1. Acierto (con su intervalo), F1 macro, tiempo y coste por cada mil textos.
2. Dónde falla cada uno: la matriz de confusión del mejor y del LLM local.
3. ¿Es real la diferencia? McNemar, caso a caso.
4. La trampa de las etiquetas: comparar por número en lugar de por nombre.

Necesita `uv sync --group hf` y Ollama con qwen3:8b y bge-m3. El LLM local tarda cerca de
una hora en la máquina del curso; los encoders, unos minutos. Con --grabadas, un segundo.
Uso: `uv run python modulos/b-hugging-face/sentimiento.py [--grabadas] [--llm chat_hf]
[--solo NOMBRE]`
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Literal

import datos
from curso_core import ClienteLLM, ErrorFormato, ErrorLLM, Opciones, prompts
from curso_core.evals import Informe, ResultadoCaso, comparar, intervalo_wilson, prueba_mcnemar
from dotenv import load_dotenv
from pydantic import BaseModel

RESULTADOS = Path(__file__).resolve().parent / "resultados"
ENCODERS = [
    "UMUTeam/roberta-spanish-sentiment-analysis",
    "clapAI/modernBERT-base-multilingual-sentiment",
    "lxyuan/distilbert-base-multilingual-cased-sentiments-student",
]
TRAMPA = ENCODERS[2]  # devuelve 0 = positive y 2 = negative: al revés que el dataset
OPCIONES_LLM = Opciones(temperatura=0, max_tokens=50, razonar=False)


class Sentimiento(BaseModel):
    sentimiento: Literal["negative", "neutral", "positive"]


def informe(nombre: str, esperadas: list[str], predichas: list[str], detalle: dict) -> Informe:
    resultados = [
        ResultadoCaso(caso=f"test-{i:03d}", ok=p == e, salida=p, detalle={"esperada": e})
        for i, (e, p) in enumerate(zip(esperadas, predichas, strict=True))
    ]
    return Informe(version=nombre, resultados=resultados, meta=detalle)


def con_encoder(modelo: str, textos: list[str], esperadas: list[str]) -> Informe:
    import torch
    from transformers import pipeline

    clasificador = pipeline("text-classification", model=modelo, device="cpu")
    clasificador(textos[:8])  # calentar: la primera llamada incluye inicializaciones
    inicio = time.perf_counter()
    salidas = clasificador(textos, batch_size=32, truncation=True)
    segundos = time.perf_counter() - inicio
    ids = [clasificador.model.config.label2id[s["label"]] for s in salidas]
    detalle = {
        "segundos": segundos,
        "coste_usd": 0.0,
        "parametros": sum(p.numel() for p in clasificador.model.parameters()),
        "hilos": torch.get_num_threads(),
        "ids": ids,  # el número de clase que devuelve el modelo, para la parte 4
        "etiquetas": clasificador.model.config.id2label,
    }
    return informe(modelo, esperadas, [s["label"].lower() for s in salidas], detalle)


def con_llm(rol: str, textos: list[str], esperadas: list[str]) -> Informe:
    cliente = ClienteLLM()
    cliente.descargar_modelo(rol)
    plantilla = prompts.cargar("hf/sentimiento")
    predichas, coste, segundos = [], 0.0, 0.0
    for texto in textos:
        mensajes = prompts.renderizar(plantilla, texto=texto)
        try:
            resultado, r = cliente.extraer(mensajes, Sentimiento, rol=rol, opciones=OPCIONES_LLM)
            predichas.append(resultado.sentimiento)
            coste += r.coste_usd or 0.0
            segundos += r.latencia_s
        except (ErrorFormato, ErrorLLM) as e:
            predichas.append(f"error: {str(e)[:60]}")
    _, _, modelo = cliente.config.resolver(rol)
    detalle = {"segundos": segundos, "coste_usd": coste, "modelo": modelo}
    return informe(f"llm:{rol}", esperadas, predichas, detalle)


def con_embeddings(textos: list[str], esperadas: list[str]) -> Informe:
    from sklearn.linear_model import LogisticRegression

    cliente = ClienteLLM()

    def vectores(xs: list[str]) -> tuple[list[list[float]], float]:
        salida, segundos = [], 0.0
        for i in range(0, len(xs), 32):
            e = cliente.embeber(xs[i : i + 32])
            salida += e.vectores
            segundos += e.latencia_s
        return salida, segundos

    textos_train, etiquetas_train = datos.cargar("train")
    x_train, _ = vectores(textos_train)
    modelo = LogisticRegression(max_iter=2000).fit(x_train, etiquetas_train)
    x_test, segundos = vectores(textos)
    inicio = time.perf_counter()
    predichas = list(modelo.predict(x_test))
    segundos += time.perf_counter() - inicio
    detalle = {"segundos": segundos, "coste_usd": 0.0, "entrenamiento": len(textos_train)}
    return informe("embeddings+regresion", esperadas, predichas, detalle)


def f1_macro(inf: Informe) -> float:
    """La media del F1 de cada clase: no deja que una clase fácil tape a una difícil."""
    f1s = []
    for clase in datos.ETIQUETAS:
        aciertos = sum(r.ok and r.salida == clase for r in inf.resultados)
        predichas = sum(r.salida == clase for r in inf.resultados)
        reales = sum(r.detalle["esperada"] == clase for r in inf.resultados)
        precision = aciertos / predichas if predichas else 0.0
        exhaustividad = aciertos / reales if reales else 0.0
        suma = precision + exhaustividad
        f1s.append(2 * precision * exhaustividad / suma if suma else 0.0)
    return sum(f1s) / len(f1s)


def confusion(inf: Informe) -> list[str]:
    filas = [f"   {'esperada → predicha':22}" + "".join(f"{e:>10}" for e in datos.ETIQUETAS)]
    for esperada in datos.ETIQUETAS:
        rs = [r for r in inf.resultados if r.detalle["esperada"] == esperada]
        cuentas = [sum(r.salida == p for r in rs) for p in datos.ETIQUETAS]
        filas.append(f"   {esperada:22}" + "".join(f"{c:>10}" for c in cuentas))
    return filas


def nombre_corto(version: str) -> str:
    return version.split("/")[-1][:34]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a ningún modelo")
    parser.add_argument("--llm", action="append", default=[], help="otro rol de LLM (repetible)")
    parser.add_argument("--solo", help="ejecuta solo ese sistema (p. ej. llm:agente) y guarda")
    args = parser.parse_args()
    load_dotenv()  # HF_TOKEN, si está (opcional)
    sistemas = [*ENCODERS, "llm:agente", *[f"llm:{r}" for r in args.llm], "embeddings+regresion"]

    def ruta(nombre: str) -> Path:
        return RESULTADOS / f"sentimiento-{nombre.replace('/', '__').replace(':', '-')}.jsonl"

    if not args.grabadas:
        textos, esperadas = datos.cargar("test")
        for s in sistemas:
            if args.solo and s != args.solo:
                continue
            if s.startswith("llm:"):
                inf = con_llm(s.removeprefix("llm:"), textos, esperadas)
            elif s == "embeddings+regresion":
                inf = con_embeddings(textos, esperadas)
            else:
                inf = con_encoder(s, textos, esperadas)
            inf.guardar(ruta(s))
            print(f"   {s}: {inf.aciertos} de {inf.total}", file=sys.stderr)
    informes = {s: Informe.cargar(ruta(s)) for s in sistemas if ruta(s).exists()}

    n = next(iter(informes.values())).total
    print(
        f"1. Sentimiento en {n} tuits en español (un tercio de cada clase; el azar acierta un 33 %)"
    )
    cabecera = f"{'acierto':>8} {'IC 95 %':>13} {'F1 macro':>9} {'s/1000':>7} {'$/1000':>7}"
    print(f"   {'sistema':36} {cabecera}")
    for s, inf in informes.items():
        bajo, alto = intervalo_wilson(inf.aciertos, inf.total)
        por_mil = 1000 / inf.total
        segundos, coste = inf.meta["segundos"] * por_mil, inf.meta["coste_usd"] * por_mil
        print(
            f"   {nombre_corto(s):36} {inf.aciertos / inf.total:>8.1%} "
            f"{f'{bajo:.0%}-{alto:.0%}':>13} {f1_macro(inf):>9.2f} {segundos:>7.0f} {coste:>7.3f}"
        )

    encoders = {s: informes[s] for s in ENCODERS if s in informes}
    mejor = max(encoders, key=lambda s: encoders[s].aciertos)
    print(f"\n2. Dónde falla: {nombre_corto(mejor)}")
    print("\n".join(confusion(informes[mejor])))
    if "llm:agente" in informes:
        print(f"   y el LLM local ({informes['llm:agente'].meta['modelo']}):")
        print("\n".join(confusion(informes["llm:agente"])))
        errores = [
            r.salida for r in informes["llm:agente"].resultados if r.salida.startswith("error")
        ]
        print(f"   respuestas que no cumplieron el esquema: {len(errores)}")

    print("\n3. ¿Es real la diferencia? (McNemar, caso a caso)")
    for s in informes:
        if s == mejor:
            continue
        c = comparar(informes[s], informes[mejor])
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        print(
            f"   {nombre_corto(mejor)} frente a {nombre_corto(s)}: "
            f"gana {len(c.ganados)}, pierde {len(c.perdidos)}, p = {p:.3f}"
        )

    if TRAMPA in informes:
        inf = informes[TRAMPA]
        esperadas_id = [datos.ETIQUETAS.index(r.detalle["esperada"]) for r in inf.resultados]
        por_numero = sum(a == b for a, b in zip(inf.meta["ids"], esperadas_id, strict=True))
        print(f"\n4. La trampa de las etiquetas: {nombre_corto(TRAMPA)}")
        print(f"   el modelo:  {inf.meta['etiquetas']}")
        print(f"   el dataset: { {i: e for i, e in enumerate(datos.ETIQUETAS)} }")
        print(f"   comparando por nombre: {inf.aciertos / inf.total:.1%}")
        print(f"   comparando por número: {por_numero / inf.total:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

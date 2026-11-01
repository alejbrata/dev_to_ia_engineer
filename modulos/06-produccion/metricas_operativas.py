"""Lección 6.03: las métricas del asistente, en tráfico normal y en un pico.

1. Dos fases de tráfico contra el servicio: normal (30 preguntas, una tras otra, con
   repeticiones) y un pico (8 preguntas nuevas a la vez). Tras cada una, se lee /metrics.
2. Por fase: preguntas por resultado, latencia p50 y p95 (del histograma y exacta), tasa
   de caché y de respaldo, tokens por pregunta y coste si fuera una API.
3. Los objetivos de servicio (SLO), fase a fase.
4. La latencia según quién la mida: el servidor, un cliente que reutiliza la conexión y
   uno que abre una por petición.

Necesita Ollama con los modelos del módulo 4 y el reranker. Tarda unos 10 minutos en la
máquina del curso; con --grabadas, un segundo.
Uso: `uv run python modulos/06-produccion/metricas_operativas.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

import httpx
from arquitectura import CLIENTE, URL, Servidor, preguntar, preguntas_del_dataset, trafico

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
GENERAN = ("chat_grande", "chat")  # los roles que generan: los que cobraría una API
REFERENCIA = ("openai", "gpt-6-luna")  # precio de referencia (config/models.toml)
SLO = {"p95_s": 30.0, "respaldo": 0.05, "degradadas": 0}


def raspar() -> dict[tuple, float]:
    """Lee /metrics como lo haría Prometheus: {(métrica, etiquetas...): valor}."""
    from prometheus_client.parser import text_string_to_metric_families

    valores = {}
    for familia in text_string_to_metric_families(CLIENTE.get(f"{URL}/metrics/").text):
        for m in familia.samples:
            valores[(m.name, *sorted(m.labels.items()))] = m.value
    return valores


def diferencia(despues: dict, antes: dict) -> dict:
    return {k: v - antes.get(k, 0.0) for k, v in despues.items()}


def suma(valores: dict, nombre: str, **filtro) -> float:
    total = 0.0
    for (n, *etiquetas), v in valores.items():
        e = dict(etiquetas)
        if n == nombre and all(e.get(k) in vs for k, vs in filtro.items()):
            total += v
    return total


def cuantil(q: float, valores: dict, resultados: tuple[str, ...]) -> float:
    """Como histogram_quantile de Prometheus: busca la cubeta del cuantil e interpola
    dentro de ella, suponiendo los valores repartidos por igual."""
    cubetas = defaultdict(float)
    for (n, *etiquetas), v in valores.items():
        e = dict(etiquetas)
        if n == "asistente_duracion_segundos_bucket" and e["resultado"] in resultados:
            cubetas[float(e["le"])] += v
    limites = sorted(cubetas)
    total = cubetas[limites[-1]]
    objetivo, anterior, acumulado_anterior = q * total, 0.0, 0.0
    for limite in limites:
        if cubetas[limite] >= objetivo:
            if limite == float("inf"):
                return anterior
            dentro = cubetas[limite] - acumulado_anterior
            return anterior + (limite - anterior) * (objetivo - acumulado_anterior) / dentro
        anterior, acumulado_anterior = limite, cubetas[limite]
    return anterior


def percentil(xs: list[float], q: float) -> float:
    ordenados = sorted(xs)
    return ordenados[min(len(ordenados) - 1, round(q * (len(ordenados) - 1)))]


def fase(valores: dict, respuestas: list[dict], precio) -> dict:
    por_resultado = {
        r: suma(valores, "asistente_preguntas_total", resultado=(r,))
        for r in ("cache", "principal", "respaldo", "degradada")
    }
    total = sum(por_resultado.values())
    generadas = por_resultado["principal"] + por_resultado["respaldo"]
    entrada = suma(valores, "llm_tokens_total", rol=GENERAN, tipo=("entrada",))
    salida = suma(valores, "llm_tokens_total", rol=GENERAN, tipo=("salida",))
    coste = (entrada * precio.entrada + salida * precio.salida) / 1e6
    exactas = [r["ms"] / 1000 for r in respuestas if not r["cache"]]
    return {
        "preguntas": por_resultado,
        "p50_s": cuantil(0.5, valores, ("principal", "respaldo")),
        "p95_s": cuantil(0.95, valores, ("principal", "respaldo")),
        "p50_exacto_s": percentil(exactas, 0.5),
        "p95_exacto_s": percentil(exactas, 0.95),
        "cache": por_resultado["cache"] / total,
        "respaldo": por_resultado["respaldo"] / generadas if generadas else 0.0,
        "tokens_por_pregunta": [entrada / generadas, salida / generadas],
        "coste_por_mil_usd": coste / total * 1000,
    }


def latencia_segun_quien(pregunta: str) -> dict:
    servidor, compartido, suelto = [], [], []
    for _ in range(30):
        t0 = time.perf_counter()
        r = CLIENTE.post(f"{URL}/preguntas", json={"pregunta": pregunta}).json()
        compartido.append((time.perf_counter() - t0) * 1000)
        servidor.append(r["ms"])
        t0 = time.perf_counter()
        httpx.post(f"{URL}/preguntas", json={"pregunta": pregunta}, timeout=60)
        suelto.append((time.perf_counter() - t0) * 1000)
    return {
        "servidor": median(servidor),
        "cliente compartido": median(compartido),
        "cliente por petición": median(suelto),
    }


def medir() -> dict:
    from curso_core import config as cfg

    precio = cfg.cargar().precio(*REFERENCIA)
    preguntas = preguntas_del_dataset()
    salida = {"referencia": "/".join(REFERENCIA), "slo": SLO}
    with Servidor(cache=True):
        preguntar(preguntas[41])  # calentar
        inicio = raspar()
        normal = [preguntar(p) for p in trafico(preguntas[:10], 30)]
        tras_normal = raspar()
        with ThreadPoolExecutor(8) as ex:
            pico = list(ex.map(preguntar, preguntas[30:38]))
        tras_pico = raspar()
        salida["normal"] = fase(diferencia(tras_normal, inicio), normal, precio)
        salida["pico"] = fase(diferencia(tras_pico, tras_normal), pico, precio)
        salida["latencia_segun_quien"] = latencia_segun_quien(preguntas[0])
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a nada")
    args = parser.parse_args()
    ruta = RESULTADOS / "metricas.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    fases = ("normal", "pico")
    print("1-2. Las dos fases, leídas de /metrics")
    print(f"   {'':34} {'normal':>12} {'pico':>12}")
    filas = [
        ("preguntas: caché", lambda f: f"{f['preguntas']['cache']:.0f}"),
        ("preguntas: modelo principal", lambda f: f"{f['preguntas']['principal']:.0f}"),
        ("preguntas: respaldo", lambda f: f"{f['preguntas']['respaldo']:.0f}"),
        ("preguntas: degradadas", lambda f: f"{f['preguntas']['degradada']:.0f}"),
        ("p50 sin caché (histograma)", lambda f: f"{f['p50_s']:.1f} s"),
        ("p50 sin caché (exacto)", lambda f: f"{f['p50_exacto_s']:.1f} s"),
        ("p95 sin caché (histograma)", lambda f: f"{f['p95_s']:.1f} s"),
        ("p95 sin caché (exacto)", lambda f: f"{f['p95_exacto_s']:.1f} s"),
        ("tasa de caché", lambda f: f"{f['cache']:.0%}"),
        ("tasa de respaldo (sin caché)", lambda f: f"{f['respaldo']:.0%}"),
        (
            "tokens por pregunta generada",
            lambda f: "{:.0f}→{:.0f}".format(*f["tokens_por_pregunta"]),
        ),
        (f"$/1000 preguntas ({r['referencia']})", lambda f: f"{f['coste_por_mil_usd']:.3f}"),
    ]
    for nombre, valor in filas:
        print(f"   {nombre:34} {valor(r['normal']):>12} {valor(r['pico']):>12}")

    print("\n3. Objetivos de servicio (SLO)")
    slo = r["slo"]
    comprobaciones = [
        (f"p95 sin caché < {slo['p95_s']:.0f} s", lambda f: f["p95_s"] < slo["p95_s"]),
        (f"respaldo < {slo['respaldo']:.0%}", lambda f: f["respaldo"] < slo["respaldo"]),
        ("ninguna degradada", lambda f: f["preguntas"]["degradada"] <= slo["degradadas"]),
    ]
    for nombre, cumple in comprobaciones:
        marcas = "".join(f"{'cumple' if cumple(r[x]) else 'INCUMPLE':>12}" for x in fases)
        print(f"   {nombre:34} {marcas}")

    q = r["latencia_segun_quien"]
    print("\n4. La misma pregunta, desde la caché: ¿cuánto tarda? (mediana de 30)")
    for quien, ms in q.items():
        # El servidor redondea a milisegundos enteros: 0 quiere decir menos de 1 ms.
        texto = "< 1 ms" if ms < 1 else f"{ms:.1f} ms"
        print(f"   según {quien:22} {texto:>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

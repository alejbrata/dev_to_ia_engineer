"""Lección 6.02: el asistente con trazas de OpenTelemetry, y qué se aprende de ellas.

1. La traza de una pregunta, como cascada: qué etapa empieza cuándo y cuánto dura.
2. La traza de la misma pregunta servida por la caché.
3. Dónde se va el tiempo, sumando las etapas de varias preguntas.
4. Lo que cuesta trazar: la misma carga con trazas y sin ellas.

Arranca el servicio con ASISTENTE_TRAZAS=1, que guarda los spans en un JSONL. Con --jaeger
levanta además Jaeger en Docker y le envía las trazas por OTLP: las verás en
http://127.0.0.1:16687. Tarda unos 10 minutos; con --grabadas, un segundo.
Uso: `uv run python modulos/06-produccion/observar.py [--grabadas] [--jaeger]`
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median

import httpx
import observabilidad

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
URL = "http://127.0.0.1:8100"
# Un cliente HTTP para todas las peticiones: crear uno por petición cuesta unos 300 ms
# en Windows, más que lo que tarda el servicio en responder desde la caché (lección 6.03).
CLIENTE = httpx.Client(timeout=600)
JAEGER = "jaegertracing/jaeger:2.22.0"
# Puertos distintos de los habituales (16686 y 4318) para no chocar con otro Jaeger que ya
# tengas en marcha: dentro del contenedor siguen siendo los de siempre.
PUERTO_UI, PUERTO_OTLP = 16687, 4319
N_COSTE = 200
sys.path.insert(0, str(AQUI.parent / "04-evals"))


class Servidor:
    def __init__(self, entorno: dict[str, str]):
        self.entorno = entorno

    def __enter__(self):
        self.proceso = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "servicio:app",
                "--app-dir",
                str(AQUI),
                "--port",
                "8100",
                "--log-level",
                "warning",
            ],
            env=os.environ | self.entorno,
            # En Windows, un grupo de procesos propio para poder pararlo con Ctrl+Break.
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        for _ in range(300):
            try:
                CLIENTE.get(f"{URL}/salud", timeout=2)
                return self
            except httpx.HTTPError:
                time.sleep(1)
        raise RuntimeError("El servicio no arrancó")

    def __exit__(self, *_):
        # Parada ordenada, para que el servicio envíe los spans que le quedan (la anatomía):
        # SIGTERM en Linux y macOS; en Windows, terminate() mata el proceso sin avisar, así
        # que se manda Ctrl+Break, que uvicorn también atiende.
        if os.name == "nt":
            self.proceso.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            self.proceso.terminate()
        try:
            self.proceso.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.proceso.kill()
            self.proceso.wait()


def preguntar(pregunta: str) -> dict:
    return CLIENTE.post(f"{URL}/preguntas", json={"pregunta": pregunta}, timeout=600).json()


def arboles(spans: list[dict]) -> dict[str, list[dict]]:
    por_traza = defaultdict(list)
    for s in spans:
        por_traza[s["traza"]].append(s)
    return por_traza


def cascada(spans: list[dict]) -> list[str]:
    """Cada span con su sangría, cuándo empieza (desde la raíz) y cuánto dura."""
    raiz = next(s for s in spans if s["padre"] is None)
    hijos = defaultdict(list)
    for s in spans:
        hijos[s["padre"]].append(s)
    lineas = []

    def visitar(s: dict, nivel: int) -> None:
        desde = (s["inicio_ns"] - raiz["inicio_ns"]) / 1e6
        a = s["atributos"]
        extra = []
        if "gen_ai.usage.input_tokens" in a:
            entrada = a["gen_ai.usage.input_tokens"]
            extra.append(f"{entrada}→{a.get('gen_ai.usage.output_tokens', 0)} tokens")
        for clave in ("asistente.cache", "asistente.fallback", "asistente.rol"):
            if clave in a:
                extra.append(f"{clave.split('.')[1]}={a[clave]}")
        nombre = "  " * nivel + s["nombre"]
        lineas.append(f"   {nombre[:44]:44} {desde:>8.0f} ms {s['ms']:>8.0f} ms  {' '.join(extra)}")
        for h in sorted(hijos[s["span"]], key=lambda x: x["inicio_ns"]):
            visitar(h, nivel + 1)

    visitar(raiz, 0)
    return lineas


def etapa(nombre: str) -> str:
    operacion = nombre.split(" ")[0]
    return {"chat": "generar (chat)", "embeddings": "embeddings", "rerank": "reordenar"}.get(
        operacion, "resto"
    )


def con_jaeger() -> subprocess.Popen | None:
    subprocess.run(["docker", "rm", "-f", "jaeger-curso"], capture_output=True)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            "jaeger-curso",
            "-p",
            f"127.0.0.1:{PUERTO_UI}:16686",
            "-p",
            f"127.0.0.1:{PUERTO_OTLP}:4318",
            JAEGER,
        ],
        check=True,
        capture_output=True,
    )
    for _ in range(60):
        try:
            httpx.get(f"http://127.0.0.1:{PUERTO_UI}/api/v3/services", timeout=2).raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(1)


def medir(jaeger: bool) -> dict:
    import dataset

    preguntas = [c.pregunta for c in dataset.cargar() if c.debe_responder]
    fichero = Path(tempfile.mkdtemp()) / "otel.jsonl"
    entorno = {"ASISTENTE_TRAZAS": "1", "OTEL_FICHERO": str(fichero)}
    if jaeger:
        con_jaeger()
        entorno["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"http://127.0.0.1:{PUERTO_OTLP}"
    with Servidor(entorno):
        preguntar(preguntas[20])  # calentar
        distintas = [preguntar(p) for p in preguntas[:4]]
        repetida = preguntar(preguntas[0])
    spans = observabilidad.leer(fichero)
    todas = arboles(spans)
    raices = {t: next(s for s in ss if s["padre"] is None) for t, ss in todas.items()}
    # Al arrancar, el índice hace llamadas de embeddings que forman trazas propias, sin
    # petición detrás: aquí solo interesan las de las preguntas.
    trazas = {t: ss for t, ss in todas.items() if raices[t]["nombre"] == "POST /preguntas"}
    # Las trazas, en orden de llegada: calentar, 4 distintas y la repetida.
    orden = sorted(trazas, key=lambda t: raices[t]["inicio_ns"])
    salida = {
        "spans": len(spans),
        "trazas": len(todas),
        "trazas_preguntas": len(trazas),
        "cascada": cascada(trazas[orden[1]]),
        "cascada_cache": cascada(trazas[orden[-1]]),
        "respuestas_ms": [r["ms"] for r in distintas] + [repetida["ms"]],
    }
    tiempos = defaultdict(float)
    for t in orden[1:5]:
        raiz = raices[t]
        hijos = [s for s in trazas[t] if s["padre"] is not None]
        hojas = [s for s in hijos if etapa(s["nombre"]) != "resto"]
        for s in hojas:
            tiempos[etapa(s["nombre"])] += s["ms"]
        tiempos["resto"] += raiz["ms"] - sum(s["ms"] for s in hojas)
    salida["etapas_ms"] = dict(tiempos)
    if jaeger:
        # Jaeger 2 consulta con su API v3 (la /api/... de Jaeger 1 ya no existe).
        ahora = datetime.now(UTC)
        r = httpx.get(
            f"http://127.0.0.1:{PUERTO_UI}/api/v3/traces",
            params={
                "query.service_name": "asistente-documentacion",
                "query.start_time_min": (ahora - timedelta(hours=1)).isoformat(),
                "query.start_time_max": ahora.isoformat(),
            },
        ).json()
        salida["jaeger_trazas"] = len(
            {
                s["traceId"]
                for rs in r["result"]["resourceSpans"]
                for ss in rs["scopeSpans"]
                for s in ss["spans"]
            }
        )
        subprocess.run(["docker", "rm", "-f", "jaeger-curso"], capture_output=True)

    # Lo que cuesta trazar: 200 peticiones servidas por la caché, con y sin trazas (solo al
    # fichero: Jaeger ya está parado). Desde la caché, el modelo no tapa la diferencia.
    coste = {}
    solo_fichero = {"ASISTENTE_TRAZAS": "1", "OTEL_FICHERO": str(fichero.with_name("coste.jsonl"))}
    for nombre, extra in (("sin trazas", {}), ("con trazas", solo_fichero)):
        with Servidor(extra):
            preguntar(preguntas[0])
            ms = []
            for _ in range(N_COSTE):
                t0 = time.perf_counter()
                preguntar(preguntas[0])
                ms.append((time.perf_counter() - t0) * 1000)
        coste[nombre] = median(ms)
    salida["coste_ms"] = coste
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a nada")
    parser.add_argument("--jaeger", action="store_true", help="envía las trazas a Jaeger (Docker)")
    args = parser.parse_args()
    ruta = RESULTADOS / "observabilidad.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir(args.jaeger)
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{r['spans']} spans en {r['trazas']} trazas, {r['trazas_preguntas']} de preguntas")
    print("\n1. Una pregunta, como cascada")
    print(f"   {'span':44} {'empieza':>11} {'dura':>11}")
    print("\n".join(r["cascada"]))
    print("\n2. La misma pregunta, desde la caché")
    print("\n".join(r["cascada_cache"]))
    total = sum(r["etapas_ms"].values())
    print("\n3. Dónde se va el tiempo (4 preguntas distintas)")
    for nombre, ms in sorted(r["etapas_ms"].items(), key=lambda x: -x[1]):
        print(f"   {nombre:16} {ms / 1000:>7.1f} s {ms / total:>6.1%}")
    if "jaeger_trazas" in r:
        print(f"   Jaeger recibió {r['jaeger_trazas']} trazas")
    c = r["coste_ms"]
    print(f"\n4. Lo que cuesta trazar ({N_COSTE} peticiones desde la caché, mediana)")
    print(f"   sin trazas {c['sin trazas']:.2f} ms · con trazas {c['con trazas']:.2f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())

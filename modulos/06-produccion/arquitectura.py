"""Lección 6.01: el asistente como servicio, medido. Caché, concurrencia, cola y fallback.

1. Una petición a la API, por dentro.
2. Tráfico con preguntas repetidas, sin caché y con caché: latencia y aciertos de caché.
3. Seis preguntas a la vez: en serie, en paralelo y por la cola.
4. El modelo principal cae: cuánto tarda el fallback según cómo cae y cómo está configurado.
5. Lo que cuesta el fallback en calidad: el modelo de respaldo con la eval del módulo 4.

Arranca el servicio (servicio.py) en el puerto 8100 cuando lo necesita. Necesita Ollama
con los modelos del módulo 4 y el reranker de la lección 3.05 en marcha. Tarda cerca de
una hora en la máquina del curso; con --grabadas, un segundo.
Uso: `uv run python modulos/06-produccion/arquitectura.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import os
import random
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

import httpx

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
URL = "http://127.0.0.1:8100"
# Un cliente HTTP para todas las peticiones: crear uno por petición cuesta unos 300 ms
# en Windows, más que lo que tarda el servicio en responder desde la caché (lección 6.03).
CLIENTE = httpx.Client(timeout=600)
sys.path.insert(0, str(AQUI.parent / "04-evals"))


def preguntas_del_dataset() -> list[str]:
    import dataset

    return [c.pregunta for c in dataset.cargar() if c.debe_responder]


def trafico(distintas: list[str], n: int) -> list[str]:
    """n peticiones con repeticiones, como el tráfico real: unas pocas preguntas se repiten
    mucho y la mayoría poco (pesos de Zipf: la i-ésima pregunta, con peso 1/i)."""
    rng = random.Random(0)
    return rng.choices(distintas, weights=[1 / (i + 1) for i in range(len(distintas))], k=n)


class Servidor:
    """Lanza el servicio en un subproceso y espera a que responda."""

    def __init__(self, cache: bool):
        self.cache = cache

    def __enter__(self):
        entorno = os.environ | {"ASISTENTE_CACHE": "1" if self.cache else "0"}
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
            env=entorno,
        )
        for _ in range(300):
            try:
                CLIENTE.get(f"{URL}/salud", timeout=2)
                return self
            except httpx.HTTPError:
                time.sleep(1)
        raise RuntimeError("El servicio no arrancó")

    def __exit__(self, *_):
        self.proceso.terminate()
        self.proceso.wait()


def preguntar(pregunta: str) -> dict:
    inicio = time.perf_counter()
    r = CLIENTE.post(f"{URL}/preguntas", json={"pregunta": pregunta}, timeout=600).json()
    return r | {"ms_cliente": round((time.perf_counter() - inicio) * 1000)}


def resumen(ms: list[int]) -> dict:
    ordenados = sorted(ms)
    p95 = ordenados[min(len(ordenados) - 1, round(0.95 * (len(ordenados) - 1)))]
    return {
        "n": len(ms),
        "p50_s": median(ms) / 1000,
        "p95_s": p95 / 1000,
        "total_s": sum(ms) / 1000,
    }


def parte_cache(preguntas: list[str]) -> dict:
    peticiones = trafico(preguntas[:12], 40)
    salida = {"peticiones": len(peticiones), "distintas": len(set(peticiones))}
    for cache in (False, True):
        with Servidor(cache):
            preguntar(preguntas[20])  # calentar: carga el modelo en memoria
            rs = [preguntar(p) for p in peticiones]
            salud = CLIENTE.get(f"{URL}/salud").json()
        salida["con cache" if cache else "sin cache"] = resumen([r["ms_cliente"] for r in rs]) | {
            "aciertos_cache": sum(r["cache"] for r in rs)
        }
        salida["salud"] = salud
    return salida


def parte_concurrencia(preguntas: list[str]) -> dict:
    seis = preguntas[30:36]
    salida = {}
    with Servidor(cache=False):
        preguntar(preguntas[20])
        inicio = time.perf_counter()
        serie = [preguntar(p) for p in seis]
        salida["en serie"] = resumen([r["ms_cliente"] for r in serie]) | {
            "pared_s": time.perf_counter() - inicio,
            "respaldo": sum(r["fallback"] for r in serie),
        }
        inicio = time.perf_counter()
        with ThreadPoolExecutor(6) as ex:
            paralelo = list(ex.map(preguntar, seis))
        salida["a la vez"] = resumen([r["ms_cliente"] for r in paralelo]) | {
            "pared_s": time.perf_counter() - inicio,
            # Todas llegan a la vez a un Ollama que atiende de una en una: las últimas
            # esperan en su cola, y si pasan del timeout responde el modelo de respaldo.
            "respaldo": sum(r["fallback"] for r in paralelo),
        }
        inicio = time.perf_counter()
        encolar = []
        for p in seis:
            t0 = time.perf_counter()
            encolar.append(
                (
                    CLIENTE.post(f"{URL}/trabajos", json={"pregunta": p}).json()["id"],
                    round((time.perf_counter() - t0) * 1000),
                )
            )
        pendientes, hechos = {i for i, _ in encolar}, []
        while pendientes:
            time.sleep(1)
            for i in list(pendientes):
                trabajo = CLIENTE.get(f"{URL}/trabajos/{i}").json()
                if trabajo["estado"] == "hecho":
                    pendientes.discard(i)
                    hechos.append(trabajo["resultado"])
        salida["por la cola"] = {
            "respuesta_al_encolar_ms": median(ms for _, ms in encolar),
            "pared_s": time.perf_counter() - inicio,
            "respaldo": sum(r["fallback"] for r in hechos),
        }
    return salida


class Colgado:
    """Un servidor que acepta la conexión y no contesta nunca: un modelo colgado."""

    def __enter__(self):
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen()
        self.puerto = self.socket.getsockname()[1]
        self.conexiones = []
        threading.Thread(target=self._aceptar, daemon=True).start()
        return self

    def _aceptar(self):
        while True:
            try:
                self.conexiones.append(self.socket.accept()[0])
            except OSError:
                return

    def __exit__(self, *_):
        self.socket.close()


def config_con(base_url: str):
    from curso_core import config as cfg

    c = cfg.cargar()
    c.providers["caido"] = cfg.Proveedor(tipo="ollama", base_url=base_url)
    c.roles["principal"] = cfg.Rol(provider="caido", model="qwen2.5:7b")
    return c


def parte_fallback(pregunta: str) -> list[dict]:
    from asistente import Asistente

    casos = []
    libre = socket.socket()
    libre.bind(("127.0.0.1", 0))
    puerto_cerrado = libre.getsockname()[1]
    libre.close()  # nadie escucha en ese puerto: conexión rechazada al instante
    with Colgado() as colgado:
        escenarios = [
            ("rechaza la conexión", f"http://127.0.0.1:{puerto_cerrado}", 120.0, 3),
            ("se cuelga", f"http://127.0.0.1:{colgado.puerto}", 120.0, 0),
            ("se cuelga", f"http://127.0.0.1:{colgado.puerto}", 15.0, 3),
            ("se cuelga", f"http://127.0.0.1:{colgado.puerto}", 15.0, 0),
        ]
        for caida, url, timeout, reintentos in escenarios:
            a = Asistente(
                ("principal", "chat"),
                cache=False,
                timeout_s=timeout,
                reintentos=reintentos,
                config=config_con(url),
            )
            a.responder("calentar el modelo de respaldo")
            r = a.responder(pregunta)
            casos.append(
                {
                    "caida": caida,
                    "timeout_s": timeout,
                    "reintentos": reintentos,
                    "respondio": r.rol,
                    "fallback": r.fallback,
                    "s": r.ms / 1000,
                    "error": r.errores[0][:90] if r.errores else "",
                }
            )
    return casos


def parte_calidad() -> dict:
    import con_api
    import dataset
    import evaluar
    from curso_core.evals import Informe, comparar, prueba_mcnemar

    casos = dataset.cargar()
    por_id = {c.id: c for c in casos}
    respaldo = con_api.ejecutar("chat", casos)
    respaldo.guardar(RESULTADOS / "respaldo-chat.jsonl")
    vigente = Informe.cargar(evaluar.VIGENTE)
    for r in vigente.resultados:
        r.ok = dataset.puntuar(por_id[r.caso], r.salida)
    c = comparar(vigente, respaldo)
    return {
        "vigente": [vigente.aciertos, vigente.total],
        "respaldo": [respaldo.aciertos, respaldo.total],
        "modelo_respaldo": respaldo.meta["modelo"],
        "p50_respaldo_s": respaldo.meta["uso"]["latencia_p50_s"],
        "gana": len(c.ganados),
        "pierde": len(c.perdidos),
        "p": prueba_mcnemar(len(c.ganados), len(c.perdidos)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a nada")
    args = parser.parse_args()
    ruta = RESULTADOS / "arquitectura.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        preguntas = preguntas_del_dataset()
        r = {}
        with Servidor(cache=True):
            preguntar(preguntas[20])
            r["ejemplo"] = preguntar(preguntas[0])
        r["cache"] = parte_cache(preguntas)
        r["concurrencia"] = parte_concurrencia(preguntas)
        r["fallback"] = parte_fallback(preguntas[0])
        r["calidad"] = parte_calidad()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    e = r["ejemplo"]
    print("1. Una petición a POST /preguntas")
    print(f"   respuesta: {e['texto'][:90]}")
    print(f"   fuentes: {e['fuentes']}")
    print(f"   rol: {e['rol']} ({e['modelo']}) · caché: {e['cache']} · fallback: {e['fallback']}")
    print(f"   {e['ms']} ms en el servidor, {e['ms_cliente']} ms vistos desde el cliente")

    c = r["cache"]
    print(f"\n2. {c['peticiones']} peticiones, {c['distintas']} preguntas distintas")
    print(f"   {'':12} {'p50':>8} {'p95':>8} {'total':>8} {'aciertos de caché':>18}")
    for nombre in ("sin cache", "con cache"):
        x = c[nombre]
        print(
            f"   {nombre:12} {x['p50_s']:>7.3f}s {x['p95_s']:>7.3f}s {x['total_s']:>7.0f}s "
            f"{x['aciertos_cache']:>18}"
        )

    k = r["concurrencia"]
    print("\n3. Seis preguntas: en serie, a la vez y por la cola (sin caché)")
    for nombre in ("en serie", "a la vez"):
        x = k[nombre]
        print(
            f"   {nombre:12} p50 {x['p50_s']:5.1f} s · p95 {x['p95_s']:5.1f} s · "
            f"todas en {x['pared_s']:4.0f} s · respondió el respaldo: {x['respaldo']}"
        )
    x = k["por la cola"]
    print(
        f"   {'por la cola':12} cada POST responde en {x['respuesta_al_encolar_ms']:.0f} ms · "
        f"todas en {x['pared_s']:4.0f} s · respondió el respaldo: {x['respaldo']}"
    )

    print("\n4. El modelo principal cae: cuánto tarda en responder el de respaldo")
    print(
        f"   {'el principal...':22} {'timeout':>8} {'reintentos':>11} {'respuesta en':>13}  quién"
    )
    for f in r["fallback"]:
        print(
            f"   {f['caida']:22} {f['timeout_s']:>7.0f}s {f['reintentos']:>11} "
            f"{f['s']:>12.1f}s  {f['respondio']}"
        )

    q = r["calidad"]
    print(f"\n5. Calidad del respaldo ({q['modelo_respaldo']}) con la eval del módulo 4")
    print(f"   vigente (7B): {q['vigente'][0]} de {q['vigente'][1]}")
    respaldo, p50 = q["respaldo"], q["p50_respaldo_s"]
    print(f"   respaldo:     {respaldo[0]} de {respaldo[1]}, p50 {p50:.1f} s")
    print(f"   el respaldo gana {q['gana']}, pierde {q['pierde']}, p = {q['p']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

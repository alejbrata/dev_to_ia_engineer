"""Lección 6.07: dos incidentes provocados en el asistente, leídos de la alerta a la causa.

Las mismas 8 preguntas en tres situaciones, con trazas y métricas activadas:
- normal, como referencia;
- el reranker caído (su URL apunta a un puerto donde no escucha nadie);
- el modelo principal cambiado por el pequeño (CURSO_ROLES=chat_grande=chat), como si
  alguien lo hubiera cambiado en la configuración sin pasar la eval.

Para cada una se recogen las señales que hay en el servicio: /salud, las métricas, las
trazas (errores y modelos usados), los tiempos y, aparte, la calidad con el dataset del
módulo 4. Tarda unos 10 minutos; con --grabadas, un segundo.
Uso: `uv run python modulos/06-produccion/incidentes.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import tempfile
from collections import Counter
from pathlib import Path
from statistics import median

import observabilidad
from metricas_operativas import diferencia, raspar, suma
from observar import CLIENTE, URL, Servidor

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
sys.path.insert(0, str(AQUI.parent / "04-evals"))
N = 8


def puerto_cerrado() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


def situacion(entorno: dict[str, str], casos) -> dict:
    import dataset

    fichero = Path(tempfile.mkdtemp()) / "otel.jsonl"
    base = {"ASISTENTE_CACHE": "0", "ASISTENTE_TRAZAS": "1", "OTEL_FICHERO": str(fichero)}
    with Servidor(base | entorno):
        salud = CLIENTE.get(f"{URL}/salud").json()
        antes = raspar()
        respuestas = [
            CLIENTE.post(f"{URL}/preguntas", json={"pregunta": c.pregunta}).json() for c in casos
        ]
        valores = diferencia(raspar(), antes)
    spans = observabilidad.leer(fichero)
    errores = Counter(
        f"{s['nombre']}" for s in spans if s["estado"] == "ERROR" and s["padre"] is not None
    )
    modelos = Counter(
        s["atributos"]["gen_ai.request.model"]
        for s in spans
        if s["atributos"].get("gen_ai.operation.name") == "chat" and s["estado"] != "ERROR"
    )
    return {
        "version": salud["version"],
        "modelo_principal": salud["modelos"]["chat_grande"].split(" @ ")[0],
        "preguntas": {
            r: suma(valores, "asistente_preguntas_total", resultado=(r,))
            for r in ("principal", "respaldo", "degradada")
        },
        "llamadas_fallidas": {
            rol: suma(valores, "llm_llamadas_total", rol=(rol,), ok=("false",))
            for rol in ("embeddings", "reranker", "chat_grande", "chat")
        },
        "spans_con_error": dict(errores),
        "modelos_que_generaron": dict(modelos),
        "mediana_s": median(r["ms"] for r in respuestas) / 1000,
        "aciertos": sum(
            dataset.puntuar(c, r["texto"]) for c, r in zip(casos, respuestas, strict=True)
        ),
        "ejemplo": respuestas[0]["texto"],
        "error_ejemplo": next((e for r in respuestas for e in r["errores"]), ""),
    }


def medir() -> dict:
    import dataset

    casos = [c for c in dataset.cargar() if c.tipo == "con_respuesta"][:N]
    caido = f"http://127.0.0.1:{puerto_cerrado()}/v1"
    return {
        "normal": situacion({}, casos),
        "reranker caído": situacion({"CURSO_URL_LLAMACPP_RERANK": caido}, casos),
        "modelo cambiado": situacion({"CURSO_ROLES": "chat_grande=chat"}, casos),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a nada")
    args = parser.parse_args()
    ruta = RESULTADOS / "incidentes.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = medir()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    nombres = list(r)
    print(f"Las mismas {N} preguntas, en tres situaciones")
    print(f"   {'':30}" + "".join(f"{n:>18}" for n in nombres))
    filas = [
        ("versión en /salud", lambda x: x["version"][:12]),
        ("modelo principal en /salud", lambda x: x["modelo_principal"]),
        ("respondidas por el principal", lambda x: f"{x['preguntas']['principal']:.0f}"),
        ("respondidas por el respaldo", lambda x: f"{x['preguntas']['respaldo']:.0f}"),
        ("degradadas", lambda x: f"{x['preguntas']['degradada']:.0f}"),
        ("llamadas fallidas: reranker", lambda x: f"{x['llamadas_fallidas']['reranker']:.0f}"),
        (
            "llamadas fallidas: modelos",
            lambda x: "{:.0f}".format(
                x["llamadas_fallidas"]["chat_grande"] + x["llamadas_fallidas"]["chat"]
            ),
        ),
        ("mediana por pregunta", lambda x: f"{x['mediana_s']:.1f} s"),
        ("aciertos (dataset del módulo 4)", lambda x: f"{x['aciertos']} de {N}"),
    ]
    for nombre, valor in filas:
        print(f"   {nombre:30}" + "".join(f"{valor(r[n]):>18}" for n in nombres))
    for n in nombres:
        x = r[n]
        print(f"\n{n}")
        print(f"   spans con error: {x['spans_con_error'] or 'ninguno'}")
        print(f"   modelos que generaron (trazas): {x['modelos_que_generaron'] or 'ninguno'}")
        if x["error_ejemplo"]:
            print(f"   error en la respuesta: {x['error_ejemplo'][:100]}")
        print(f"   primera respuesta: {x['ejemplo'][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

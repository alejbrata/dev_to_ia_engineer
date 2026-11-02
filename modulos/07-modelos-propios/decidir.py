"""Lección 7.01: ¿prompting, RAG o fine-tuning? Lo que dicen los datos del asistente.

1. Sin documentación: los modelos de 7B y de 1,5B responden las 58 preguntas del dataset
   del módulo 4 con lo que saben por sí solos.
2. Con RAG: las mismas preguntas con el sistema vigente (7B, grabado en el módulo 4) y
   con el modelo de 1,5B en su lugar (grabado en la lección 6.01).
3. Dónde falla el de 1,5B con RAG, si la recuperación es la misma: con la respuesta en el
   contexto o sin ella.
4. Lo que cuesta cada uno.

La parte 1 llama a los modelos; las demás leen resultados grabados. Tarda unos 10 minutos
en la máquina del curso; con --grabadas, un segundo.
Uso: `uv run python modulos/07-modelos-propios/decidir.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from curso_core import config as cfg

AQUI = Path(__file__).resolve().parent
RESULTADOS = cfg.carpeta_resultados(AQUI / "resultados")
MODULO_4 = AQUI.parent / "04-evals"
sys.path.insert(0, str(MODULO_4))
ROLES = {"7B": "chat_grande", "1,5B": "chat"}


def sin_documentacion() -> dict:
    import dataset
    from curso_core import ClienteLLM, Opciones, prompts

    cliente = ClienteLLM()
    plantilla = prompts.cargar("modelos/sin-contexto")
    salida = {}
    for nombre, rol in ROLES.items():
        cliente.descargar_modelo(rol)
        respuestas = {}
        for c in dataset.cargar():
            mensajes = prompts.renderizar(plantilla, pregunta=c.pregunta)
            r = cliente.chat(mensajes, rol=rol, opciones=Opciones(temperatura=0, max_tokens=200))
            respuestas[c.id] = r.texto
        salida[nombre] = respuestas
    return salida


def leer(ruta: Path) -> dict[str, dict]:
    lineas = ruta.read_text(encoding="utf-8").splitlines()[1:]
    return {r["caso"]: r for r in map(json.loads, lineas)}


def resumen(respuestas: dict[str, str], casos) -> dict:
    import dataset

    con = [c for c in casos if c.debe_responder]
    sin = [c for c in casos if not c.debe_responder]
    inventa = sum(
        not dataset.puntuar(c, respuestas[c.id]) and not dataset.se_niega(respuestas[c.id])
        for c in con
    )
    return {
        "total": sum(dataset.puntuar(c, respuestas[c.id]) for c in casos),
        "con_respuesta": sum(dataset.puntuar(c, respuestas[c.id]) for c in con),
        "no_deben_responderse": sum(dataset.puntuar(c, respuestas[c.id]) for c in sin),
        "inventa": inventa,
        "n": [len(casos), len(con), len(sin)],
    }


def analizar(cerrado: dict) -> dict:
    import dataset
    import sistema

    casos = dataset.cargar()
    fragmentos = sistema.fragmentos()
    vigente = leer(MODULO_4 / "resultados" / "vigente.jsonl")
    pequeno = leer(AQUI.parent / "06-produccion" / "resultados" / "respaldo-chat.jsonl")
    con_rag = {
        "7B": {k: v["salida"] for k, v in vigente.items()},
        "1,5B": {k: v["salida"] for k, v in pequeno.items()},
    }
    fallos = {}
    for c in casos:
        bien_7b = dataset.puntuar(c, con_rag["7B"][c.id])
        bien_15 = dataset.puntuar(c, con_rag["1,5B"][c.id])
        if bien_7b and not bien_15:
            recuperados = [fragmentos[i] for i in vigente[c.id]["detalle"]["recuperados"]]
            en_contexto = any(dataset.relevante(f, c) for f in recuperados)
            respuesta = con_rag["1,5B"][c.id]
            if not c.debe_responder:
                tipo = "respondió cuando tocaba abstenerse"
            elif dataset.se_niega(respuesta):
                tipo = (
                    "se abstuvo, con la respuesta en el contexto"
                    if en_contexto
                    else ("se abstuvo, sin la respuesta en el contexto")
                )
            else:
                tipo = (
                    "respondió mal, con la respuesta en el contexto"
                    if en_contexto
                    else ("respondió mal, sin la respuesta en el contexto")
                )
            fallos[c.id] = {"tipo": tipo, "pregunta": c.pregunta, "respuesta": respuesta}
    return {
        "sin_documentacion": {n: resumen(r, casos) for n, r in cerrado.items()},
        "con_rag": {n: resumen(r, casos) for n, r in con_rag.items()},
        "fallos_1_5b": fallos,
        "ejemplo_inventado": next(
            (
                {"pregunta": c.pregunta, "respuesta": cerrado["7B"][c.id]}
                for c in casos
                if c.debe_responder
                and not dataset.puntuar(c, cerrado["7B"][c.id])
                and not dataset.se_niega(cerrado["7B"][c.id])
            ),
            None,
        ),
        "latencia_p50_s": {
            "7B": 11.5,  # la del sistema vigente, medida en el módulo 4 (anexo G)
            "1,5B": json.loads(
                (AQUI.parent / "06-produccion" / "resultados" / "respaldo-chat.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )["meta"]["uso"]["latencia_p50_s"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a los modelos")
    args = parser.parse_args()
    ruta_cerrado = RESULTADOS / "sin-documentacion.json"
    if args.grabadas:
        cerrado = json.loads(ruta_cerrado.read_text(encoding="utf-8"))
    else:
        cerrado = sin_documentacion()
        RESULTADOS.mkdir(exist_ok=True)
        ruta_cerrado.write_text(json.dumps(cerrado, ensure_ascii=False, indent=1), "utf-8")
    r = analizar(cerrado)

    n_total, n_con, n_sin = r["con_rag"]["7B"]["n"]
    print(f"1-2. Aciertos en las {n_total} preguntas del dataset del módulo 4")
    print(f"   {'':24} {'total':>8} {'con respuesta':>14} {'sin respuesta':>14} {'inventa':>8}")
    for modo in ("sin_documentacion", "con_rag"):
        for nombre, x in r[modo].items():
            etiqueta = (
                f"{nombre}, {'sin documentación' if modo == 'sin_documentacion' else 'con RAG'}"
            )
            print(
                f"   {etiqueta:24} {x['total']:>4} de {n_total} {x['con_respuesta']:>7} de {n_con}"
                f" {x['no_deben_responderse']:>7} de {n_sin} {x['inventa']:>8}"
            )
    e = r["ejemplo_inventado"]
    if e:
        print(f"   7B sin documentación, una que inventa: «{e['pregunta']}»")
        print(f"        → {e['respuesta'][:100]}")

    fallos = r["fallos_1_5b"]
    print(f"\n3. Las {len(fallos)} que acierta el 7B y falla el 1,5B, con la misma recuperación")
    tipos: dict[str, list[str]] = {}
    for caso, f in fallos.items():
        tipos.setdefault(f["tipo"], []).append(caso)
    for tipo, casos in sorted(tipos.items(), key=lambda x: -len(x[1])):
        print(f"   {len(casos):>2} {tipo}: {', '.join(casos)}")

    lat = r["latencia_p50_s"]
    print("\n4. Lo que cuesta (mediana por respuesta, con RAG, en la CPU del curso)")
    for nombre, s in lat.items():
        print(f"   {nombre}: {s:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

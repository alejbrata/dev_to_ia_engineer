"""Lección 6.09: la calidad del asistente en producción, sin saber la respuesta correcta.

En producción no hay dataset: nadie dice cuál era la respuesta buena. Tres de las cuatro
métricas de RAG de la lección 4.05 no lo necesitan (fidelidad, relevancia de la respuesta
y precisión del contexto) y se pueden calcular con jueces sobre una muestra del tráfico
(calidad.py). En tres partes:
1. ¿Se puede uno fiar de los jueces? Sobre las 58 respuestas grabadas del sistema vigente,
   donde sí se sabe la verdad: la precisión juzgada frente a la de los segmentos anclados,
   la relevancia frente a la corrección y cuánto tarda cada evaluación.
2. El canario de la lección 6.08, ahora con evaluación en línea: el candidato (1,5B) responde
   las mismas 58 preguntas, se reparte el mismo tráfico y cada respuesta generada se juzga.
   ¿Salta una regla de vuelta atrás sobre la fidelidad y la relevancia?
3. Cuántas evaluaciones hacen falta para ver una diferencia así, según el muestreo.

Necesita Ollama con los modelos del módulo 4 y el reranker en llama-server. Unos 30
minutos; con --grabadas, un segundo.
Uso: `uv run python modulos/06-produccion/calidad_en_produccion.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median

from curso_core import config as cfg

AQUI = Path(__file__).resolve().parent
RESULTADOS = cfg.carpeta_resultados(AQUI / "resultados")
sys.path.insert(0, str(AQUI.parent / "04-evals"))

from cambios_seguros import CANDIDATA, PETICIONES, PORCENTAJE, en_canario  # noqa: E402

# Regla de vuelta atrás sobre la calidad: con al menos MINIMO respuestas del canario
# juzgadas, si la fidelidad o la relevancia caen más de lo tolerado frente al vigente.
MINIMO = 10
TOLERANCIA = 0.10
MUESTREOS = (1.0, 0.1, 0.01)
Z_95, Z_80 = 1.96, 0.84  # confianza del 95 % y potencia del 80 %


def juzgar_todas(cliente, respuestas: list[dict], fragmentos: dict) -> list[dict]:
    import calidad

    juicios = []
    for r in respuestas:
        frags = [fragmentos[i] for i in r["fuentes"]]
        juicios.append(r | calidad.juzgar(cliente, r["pregunta"], r["texto"], frags))
    return juicios


def medir() -> dict:
    import dataset
    import evaluar
    import sistema
    from asistente import Asistente
    from curso_core import ClienteLLM
    from curso_core.evals import Informe

    casos = {c.id: c for c in dataset.cargar()}
    fragmentos = sistema.fragmentos()

    # Las respuestas del vigente son las grabadas en el módulo 4: mismo sistema.
    vigente = [
        {
            "caso": r.caso,
            "pregunta": casos[r.caso].pregunta,
            "texto": r.salida,
            "fuentes": r.detalle["recuperados"],
        }
        for r in Informe.cargar(evaluar.VIGENTE).resultados
    ]
    # Las del candidato se generan todas antes de juzgar: así Ollama no alterna modelos.
    candidata = Asistente(CANDIDATA, cache=False)
    generadas = []
    for c in casos.values():
        r = candidata.responder(c.pregunta)
        generadas.append(
            {"caso": c.id, "pregunta": c.pregunta, "texto": r.texto, "fuentes": r.fuentes}
        )
    cliente = ClienteLLM()
    return {
        "modelos": {"candidata": candidata.modelos[CANDIDATA[0]]},
        "vigente": juzgar_todas(cliente, vigente, fragmentos),
        "candidata": juzgar_todas(cliente, generadas, fragmentos),
    }


def con_verdad(juicios: list[dict]) -> list[dict]:
    """Añade lo que en producción no se sabe: si es correcta y qué fragmentos tenían el dato."""
    import dataset
    import sistema

    casos = {c.id: c for c in dataset.cargar()}
    todos = sistema.fragmentos()
    filas = []
    for j in juicios:
        caso = casos[j["caso"]]
        anclados = [dataset.relevante(todos[i], caso) for i in j["fuentes"]]
        filas.append(
            j
            | {
                "ok": dataset.puntuar(caso, j["texto"]),
                "debe_responder": caso.debe_responder,
                "anclados": anclados,
            }
        )
    return filas


def evaluaciones_necesarias(p1: float, p2: float) -> int | None:
    """Evaluaciones por versión para distinguir dos proporciones (prueba de dos proporciones,
    95 % de confianza, 80 % de potencia). None si son iguales."""
    if p1 == p2:
        return None
    media = (p1 + p2) / 2
    a = Z_95 * math.sqrt(2 * media * (1 - media))
    b = Z_80 * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return math.ceil(((a + b) / (p1 - p2)) ** 2)


def volver_atras(vigente: dict, canario: dict) -> list[str]:
    if canario["contestan"] < MINIMO:
        return [f"aún no: {canario['contestan']} juzgadas, hacen falta {MINIMO}"]
    motivos = []
    for metrica in ("fidelidad", "relevancia"):
        if vigente[metrica] - canario[metrica] > TOLERANCIA:
            motivos.append(f"{metrica}: {canario[metrica]:.0%} frente a {vigente[metrica]:.0%}")
    return motivos


def main() -> int:
    import arquitectura
    import calidad
    from curso_core.evals import acuerdo

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a los modelos")
    args = parser.parse_args()
    ruta = RESULTADOS / "calidad.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        from dotenv import load_dotenv

        load_dotenv()
        r = medir()
        RESULTADOS.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    vig, cand = con_verdad(r["vigente"]), con_verdad(r["candidata"])

    print("1. ¿Se puede uno fiar de los jueces? Las 58 respuestas grabadas del vigente")
    con = [f for f in vig if f["debe_responder"]]
    pares = [
        (a, u) for f in con for k, a in enumerate(f["anclados"], 1) for u in [k in f["utiles"]]
    ]
    a = acuerdo([x for x, _ in pares], [u for _, u in pares])
    juzgada = sum(f["precision"] for f in con) / len(con)
    anclada = sum(sum(f["anclados"]) / len(f["anclados"]) for f in con) / len(con)
    print(
        f"   precisión del contexto ({len(con)} preguntas con respuesta, {len(pares)} fragmentos)"
    )
    print(f"     con los segmentos anclados {anclada:.0%} · según el juez {juzgada:.0%}")
    print(
        f"     el juez marca útiles {a.vp + a.fp}; de ellos, anclados {a.vp}."
        f" De los {a.vp + a.fn} anclados, se le escapan {a.fn} · kappa {a.kappa:.2f}"
    )
    contestan = [f for f in vig if not f["abstiene"]]
    print(f"   relevancia de la respuesta ({len(contestan)} que no se abstienen)")
    for ok in (True, False):
        grupo = [f for f in contestan if f["ok"] == ok]
        si = sum(bool(f["relevante"]) for f in grupo)
        etiqueta = "correctas" if ok else "incorrectas"
        print(f"     {etiqueta:12} {len(grupo):2}: el juez dice que responden {si}")
    fieles = sum(bool(f["fiel"]) for f in contestan)
    print(f"   fidelidad (juez v2): {fieles} de {len(contestan)} fieles")
    segundos = [f["segundos"] for f in vig + cand]
    print(
        f"   tiempo de juez por respuesta: mediana {median(segundos):.1f} s,"
        f" máximo {max(segundos):.1f} s (tres juicios)"
    )

    print(
        f"\n2. Canario de la 6.08 con evaluación en línea: el {PORCENTAJE} % de las preguntas"
        f" a {r['modelos']['candidata'].split(' @')[0]}"
    )
    # Con caché, cada pregunta distinta se genera una vez por versión: solo esas se juzgan.
    trafico = arquitectura.trafico([f["pregunta"] for f in vig], PETICIONES)
    por_pregunta = {"vigente": {f["pregunta"]: f for f in vig}}
    por_pregunta["candidata"] = {f["pregunta"]: f for f in cand}
    juzgadas: dict[str, list[dict]] = {"vigente": [], "candidata": []}
    for pregunta in dict.fromkeys(trafico):
        version = "candidata" if en_canario(pregunta, PORCENTAJE) else "vigente"
        juzgadas[version].append(por_pregunta[version][pregunta])
    print(
        f"   {'':10} {'juzgadas':>9} {'contestan':>10} {'fidelidad':>10} {'relevancia':>11}"
        f" {'precisión':>10} {'aciertos*':>10}"
    )
    resumenes = {}
    for version, filas in juzgadas.items():
        s = resumenes[version] = calidad.resumen(filas)
        aciertos = sum(f["ok"] for f in filas) / len(filas)
        print(
            f"   {version:10} {s['evaluadas']:>9} {s['contestan']:>10} {s['fidelidad']:>10.0%}"
            f" {s['relevancia']:>11.0%} {s['precision']:>10.0%} {aciertos:>10.0%}"
        )
    print(
        "   * los aciertos no se ven en producción: aquí se conocen porque el tráfico es el dataset"
    )
    motivos = volver_atras(resumenes["vigente"], resumenes["candidata"])
    print(f"   regla de vuelta atrás: {'; '.join(motivos) if motivos else 'no salta'}")

    print("\n   Las 58 preguntas en cada versión (todo el tráfico juzgado, como en sombra)")
    completos = {"vigente": calidad.resumen(vig), "candidata": calidad.resumen(cand)}
    for version, s in completos.items():
        filas = vig if version == "vigente" else cand
        aciertos = sum(f["ok"] for f in filas) / len(filas)
        print(
            f"   {version:10} {s['evaluadas']:>9} {s['contestan']:>10} {s['fidelidad']:>10.0%}"
            f" {s['relevancia']:>11.0%} {s['precision']:>10.0%} {aciertos:>10.0%}"
        )
    motivos = volver_atras(completos["vigente"], completos["candidata"])
    print(f"   regla de vuelta atrás: {'; '.join(motivos) if motivos else 'no salta'}")

    print("\n3. Cuántas evaluaciones hacen falta para ver estas diferencias")
    print("   (por versión; 95 % de confianza y 80 % de potencia)")
    for metrica in ("fidelidad", "relevancia"):
        p1, p2 = completos["vigente"][metrica], completos["candidata"][metrica]
        n = evaluaciones_necesarias(p1, p2)
        if n is None:
            print(f"   {metrica:11} {p1:.0%} y {p2:.0%}: no hay diferencia que detectar")
            continue
        generadas = " · ".join(f"al {m:.0%}: {math.ceil(n / m)}" for m in MUESTREOS)
        print(f"   {metrica:11} {p1:.0%} frente a {p2:.0%}: {n} evaluaciones")
        print(f"   {'':11} respuestas generadas del canario, según el muestreo: {generadas}")
        horas = n * median(segundos) / 3600
        print(f"   {'':11} tiempo de juez para esas {n}: {horas:.1f} h en esta máquina")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Lección 6.10: del 👎 de los usuarios al dataset de la eval.

El tráfico y el reparto son los del canario de la lección 6.08, y las respuestas, las reales
que dieron las dos versiones (el sistema vigente, con el modelo de 7B, y el candidato, con el
de 1,5B; grabadas en las lecciones 4.07 y 6.09). Los usuarios son simulados: votan poco, y más
cuando algo va mal, pero también votan 👎 cuando el asistente se abstiene aunque abstenerse sea
lo correcto. En tres partes:
1. ¿Qué dice el 👎? Cuánta gente vota y si el 👎 separa las dos versiones como lo hace la eval.
2. La cola de revisión: los 👎 agrupados, con el veredicto de quien los revisa.
3. Al dataset: los fallos confirmados que no estaban en la eval entran en ella. Para poder
   medirlo, la eval inicial son las 30 preguntas del módulo 3, y el resto del dataset del módulo
   4 hace de preguntas nuevas de los usuarios, con su respuesta conocida.

No llama a ningún modelo. Uso: `uv run python modulos/06-produccion/bucle_feedback.py`
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from curso_core import config as cfg

AQUI = Path(__file__).resolve().parent
RESULTADOS = cfg.carpeta_resultados(AQUI / "resultados")
sys.path.insert(0, str(AQUI.parent / "04-evals"))

from cambios_seguros import PETICIONES, PORCENTAJE, en_canario  # noqa: E402

PETICIONES_FEEDBACK = 10 * PETICIONES  # un día de tráfico, con las mismas repeticiones
# Probabilidad de 👍 y de 👎 según la respuesta: (bien o mal, ¿se abstiene?). Inventadas, con
# las tres cosas que se ven en la práctica: se vota poco, se vota más cuando algo falla, y un
# "no lo sé" molesta aunque sea lo correcto.
VOTOS = {
    (True, False): (0.12, 0.02),
    (False, False): (0.04, 0.25),
    (True, True): (0.02, 0.15),
    (False, True): (0.01, 0.35),
}
REVISADOS = 10  # los grupos de 👎 que se enseñan, de la cola de revisión


def respuestas() -> dict[str, dict[str, str]]:
    """Texto de cada versión para cada caso: las respuestas reales grabadas."""
    import evaluar
    from curso_core.evals import Informe

    vigente = {r.caso: r.salida for r in Informe.cargar(evaluar.VIGENTE).resultados}
    calidad = json.loads((RESULTADOS / "calidad.json").read_text(encoding="utf-8"))
    candidata = {f["caso"]: f["texto"] for f in calidad["candidata"]}
    return {"vigente": vigente, "candidata": candidata}


def simular(casos: dict, textos: dict, semilla: int = 5) -> list[dict]:
    """Cada petición del día, con su versión, si estaba bien y el voto (o None)."""
    import arquitectura
    import dataset

    azar = random.Random(semilla)
    por_pregunta = {c.pregunta: c for c in casos.values()}
    filas = []
    for i, pregunta in enumerate(arquitectura.trafico(list(por_pregunta), PETICIONES_FEEDBACK)):
        caso = por_pregunta[pregunta]
        version = "candidata" if en_canario(pregunta, PORCENTAJE) else "vigente"
        texto = textos[version][caso.id]
        bien, abstiene = dataset.puntuar(caso, texto), dataset.se_niega(texto)
        p_util, p_no = VOTOS[bien, abstiene]
        tirada = azar.random()
        voto = True if tirada < p_util else False if tirada < p_util + p_no else None
        filas.append(
            {
                "id": f"r{i}",
                "caso": caso.id,
                "pregunta": pregunta,
                "version": version,
                "respuesta": texto,
                "bien": bien,
                "abstiene": abstiene,
                "voto": voto,
            }
        )
    return filas


def veredicto(caso, texto: str) -> str:
    """Lo que decide quien revisa el 👎. Aquí se sabe la respuesta correcta; en producción, lo
    decide una persona que lee la pregunta, la respuesta y los fragmentos."""
    import dataset

    if not dataset.puntuar(caso, texto):
        return "fallo real"
    return "abstención correcta" if dataset.se_niega(texto) else "respuesta correcta"


def main() -> int:
    import dataset
    import feedback
    from asistente import normalizar
    from curso_core.evals import intervalo_wilson, prueba_mcnemar

    casos = {c.id: c for c in dataset.cargar()}
    textos = respuestas()
    filas = simular(casos, textos)

    print(f"1. ¿Qué dice el 👎? {len(filas)} peticiones del canario de la 6.08, usuarios simulados")
    print(
        f"   {'':10} {'peticiones':>10} {'con voto':>9} {'👍':>5} {'👎':>5}"
        f" {'👎 / votos':>11} {'errores reales':>15}"
    )
    for version in ("vigente", "candidata"):
        fs = [f for f in filas if f["version"] == version]
        votos = [f for f in fs if f["voto"] is not None]
        no = sum(f["voto"] is False for f in votos)
        print(
            f"   {version:10} {len(fs):>10} {len(votos) / len(fs):>9.0%}"
            f" {len(votos) - no:>5} {no:>5} {no / len(votos):>11.0%}"
            f" {sum(not f['bien'] for f in fs) / len(fs):>15.0%}"
        )
    negativos = [f for f in filas if f["voto"] is False]
    en_fallos = sum(not f["bien"] for f in negativos)
    en_abstenciones = sum(f["bien"] and f["abstiene"] for f in negativos)
    print(
        f"   de los {len(negativos)} 👎, {en_fallos} son de respuestas mal"
        f" ({en_fallos / len(negativos):.0%}) y {en_abstenciones} de abstenciones correctas"
    )
    malas = [f for f in filas if not f["bien"]]
    vistas = sum(f["voto"] is False for f in malas)
    print(
        f"   de las {len(malas)} respuestas mal servidas, reciben 👎 {vistas}"
        f" ({vistas / len(malas):.0%})"
    )

    print("\n2. La cola de revisión: los 👎 agrupados por pregunta y versión")
    eval_inicial = {c.id for c in casos.values() if c.id.startswith("m3-")}
    en_la_eval = {normalizar(casos[i].pregunta) for i in eval_inicial}
    valoraciones = [f | {"util": f["voto"], "fuentes": []} for f in negativos]
    cola = feedback.cola_de_revision(valoraciones, en_la_eval)
    por_pregunta = {normalizar(c.pregunta): c for c in casos.values()}
    for g in cola:
        g["caso"] = por_pregunta[normalizar(g["pregunta"])]
        g["veredicto"] = veredicto(g["caso"], g["respuesta"])
    print(f"   {len(cola)} grupos; los {REVISADOS} con más 👎:")
    for g in cola[:REVISADOS]:
        eval_ = "en la eval" if g["en_la_eval"] else "nueva"
        print(
            f"   {g['votos']:>3} 👎 · {g['version']:9} · {g['veredicto']:19} · {eval_:10}"
            f" · {g['pregunta'][:48]}"
        )
    for nombre in ("fallo real", "abstención correcta", "respuesta correcta"):
        grupo = [g for g in cola if g["veredicto"] == nombre]
        nuevos = sum(not g["en_la_eval"] for g in grupo)
        print(
            f"   {nombre:19} {len(grupo):>3} grupos ({nuevos} de preguntas que no están en la eval)"
        )

    print(f"\n3. Al dataset: la eval inicial tiene las {len(eval_inicial)} preguntas del módulo 3")
    nuevos = sorted(
        {g["caso"].id for g in cola if g["veredicto"] == "fallo real" and not g["en_la_eval"]}
    )
    print(f"   fallos confirmados de preguntas nuevas: {len(nuevos)} → {', '.join(nuevos)}")
    for nombre, ids in (
        ("eval inicial", sorted(eval_inicial)),
        ("eval ampliada", sorted(eval_inicial | set(nuevos))),
    ):
        ok = {v: [dataset.puntuar(casos[i], textos[v][i]) for i in ids] for v in textos}
        gana = sum(c and not v for v, c in zip(ok["vigente"], ok["candidata"], strict=True))
        pierde = sum(v and not c for v, c in zip(ok["vigente"], ok["candidata"], strict=True))
        cifras = []
        for v in ("vigente", "candidata"):
            bajo, alto = intervalo_wilson(sum(ok[v]), len(ids))
            cifras.append(f"{v} {sum(ok[v])} de {len(ids)} [{bajo:.0%}, {alto:.0%}]")
        print(
            f"   {nombre:13} {' · '.join(cifras)}"
            f" · la candidata gana {gana}, pierde {pierde}, p = {prueba_mcnemar(gana, pierde):.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Genera los datos del reto del módulo 7: un ajuste con una fuga de datos metida a propósito.

- `eval.jsonl`: 40 preguntas con respuesta del dataset del módulo 4 (reales).
- `entrenamiento.jsonl`: 150 preguntas de los datos de ajuste del módulo 7 (reales) y 12 de la
  eval, copiadas con cambios pequeños, como pasa cuando los datos de entrenamiento salen de
  los mismos documentos o de una exportación que ya incluía la eval.
- `resultados.jsonl`: si el modelo base y el ajustado aciertan cada pregunta de la eval. Son
  simulados con semilla fija: el ajustado acierta todas las que vio en el entrenamiento, y en
  las demás, casi lo mismo que el base, como en la lección 06.

No lo leas antes de hacer el reto.
Uso: `uv run python modulos/07-modelos-propios/reto/generar_datos.py`
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MODULOS = AQUI.parents[1]
sys.path.insert(0, str(MODULOS / "04-evals"))

# Cómo se copian las preguntas de la eval: tal cual, o con cambios que no cambian la pregunta.
VARIANTES = [
    lambda p: p,
    lambda p: p,
    lambda p: p,
    lambda p: p,
    lambda p: p.lower(),
    lambda p: p.upper(),
    lambda p: p.replace("¿", ""),
    lambda p: p.replace("?", "").replace("¿", ""),
    lambda p: "  " + p.replace(" ", "  ") + " ",
    lambda p: p.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o"),
    lambda p: p.rstrip("?") + "?",
    lambda p: p.replace(",", "").lower(),
]


def generar(semilla: int = 11) -> tuple[list[dict], list[dict], list[dict]]:
    import dataset

    azar = random.Random(semilla)
    casos = [c for c in dataset.cargar() if c.debe_responder][:40]
    evaluacion = [{"id": c.id, "pregunta": c.pregunta} for c in casos]
    datos = MODULOS / "07-modelos-propios" / "resultados" / "ajuste" / "datos.jsonl"
    reales = [
        json.loads(linea)["pregunta"] for linea in datos.read_text(encoding="utf-8").splitlines()
    ]
    entrenamiento = [{"pregunta": p, "origen": "generada"} for p in reales[:150]]
    filtradas = azar.sample(range(len(evaluacion)), 12)
    for variante, i in zip(VARIANTES, filtradas, strict=True):
        entrenamiento.append(
            {"pregunta": variante(evaluacion[i]["pregunta"]), "origen": "generada"}
        )
    azar.shuffle(entrenamiento)

    # El base acierta 26 de 40: 7 de las 12 filtradas y 19 de las 28 limpias. El ajustado, las
    # 12 filtradas y, en las limpias, gana 3 y pierde 1 frente al base.
    limpias = [i for i in range(len(evaluacion)) if i not in filtradas]
    base = {i: False for i in range(len(evaluacion))}
    for i in azar.sample(filtradas, 7) + azar.sample(limpias, 19):
        base[i] = True
    ajustado = dict(base) | {i: True for i in filtradas}
    falladas, acertadas = [i for i in limpias if not base[i]], [i for i in limpias if base[i]]
    for i in azar.sample(falladas, 3):
        ajustado[i] = True
    ajustado[azar.choice(acertadas)] = False
    resultados = [
        {"id": e["id"], "base": base[i], "ajustado": ajustado[i]} for i, e in enumerate(evaluacion)
    ]
    return evaluacion, entrenamiento, resultados


def main() -> None:
    for nombre, filas in zip(("eval", "entrenamiento", "resultados"), generar(), strict=True):
        with (AQUI / f"{nombre}.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for fila in filas:
                f.write(json.dumps(fila, ensure_ascii=False) + "\n")
        print(f"{nombre}.jsonl: {len(filas)} líneas")


if __name__ == "__main__":
    main()

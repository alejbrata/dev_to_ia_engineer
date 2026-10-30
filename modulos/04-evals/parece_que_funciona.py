"""'Parece que funciona' no es una métrica: el mismo cambio, probado a mano y medido.

Cambiamos el prompt del RAG del módulo 3 (texto libre → JSON con citas) y lo comprobamos:
1. A mano, con las tres primeras preguntas, como se suele hacer.
2. Con las 30 preguntas, caso a caso.
3. Con todas las muestras posibles de 3 y de 10 preguntas: ¿cuántas veces engañan?

Guarda los resultados en modulos/04-evals/resultados/. Con --grabadas los reutiliza sin
llamar al modelo.
Uso: `uv run python modulos/04-evals/parece_que_funciona.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import random
import sys
from itertools import combinations
from pathlib import Path

import sistema  # el sistema que evaluamos: el RAG del módulo 3
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar
from sistema import corpus

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
VERSIONES = {"v1-texto-libre": "rag/con-contexto", "v2-con-citas": "rag/con-citas"}
MUESTRAS_10 = 100_000


def ejecutar(cliente: ClienteLLM, version: str, prompt: str) -> Informe:
    """Responde las 30 preguntas del módulo 3 con el RAG y un prompt."""
    indice = sistema.indice(cliente)
    cliente.descargar_modelo()
    resultados = []
    for p in corpus.preguntas():
        r = sistema.responder(cliente, indice, p.pregunta, prompt)
        resultados.append(
            ResultadoCaso(
                caso=str(p.id),
                ok=corpus.es_correcta(r.texto, p),
                salida=r.texto,
                detalle={"respondible": p.respondible, "citas": r.citas},
            )
        )
    return Informe(version=version, resultados=resultados)


def engañan(v1: Informe, v2: Informe, muestras) -> float:
    """Fracción de muestras en las que v1 empata o gana a v2."""
    a, b = v1.por_caso(), v2.por_caso()
    total = engaños = 0
    for muestra in muestras:
        total += 1
        engaños += sum(a[c].ok for c in muestra) >= sum(b[c].ok for c in muestra)
    return engaños / total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()

    informes = {}
    cliente = None if args.grabadas else ClienteLLM()
    for version, prompt in VERSIONES.items():
        ruta = RESULTADOS / f"{version}.jsonl"
        if args.grabadas:
            informes[version] = Informe.cargar(ruta)
        else:
            informes[version] = ejecutar(cliente, version, prompt)
            informes[version].guardar(ruta)
    v1, v2 = informes.values()
    preguntas = {str(p.id): p.pregunta for p in corpus.preguntas()}

    print("1. A mano: las tres primeras preguntas")
    for caso in ["1", "2", "3"]:
        print(f"   {caso}. {preguntas[caso]}")
        for informe in (v1, v2):
            r = informe.por_caso()[caso]
            marca = "bien" if r.ok else "MAL "
            print(f"      {informe.version:15} {marca}  {r.salida[:80]!r}")
    a_mano = [sum(i.por_caso()[c].ok for c in "123") for i in (v1, v2)]
    print(f"   {v1.version}: {a_mano[0]} de 3 · {v2.version}: {a_mano[1]} de 3")

    print("\n2. Las 30 preguntas")
    for informe in (v1, v2):
        print(f"   {informe.version:15} {informe.aciertos} de {informe.total}")
    c = comparar(v1, v2)
    print(f"   {v2.version} gana {c.ganados} y pierde {c.perdidos}")

    print(f"\n3. ¿Cuántas muestras hacen parecer que {v1.version} es igual o mejor?")
    casos = list(preguntas)
    todas_3 = list(combinations(casos, 3))
    print(f"   de 3 preguntas:  {engañan(v1, v2, todas_3):5.1%} de las {len(todas_3)} posibles")
    azar = random.Random(0)
    de_10 = (azar.sample(casos, 10) for _ in range(MUESTRAS_10))
    print(f"   de 10 preguntas: {engañan(v1, v2, de_10):5.1%} de {MUESTRAS_10} muestras al azar")
    return 0


if __name__ == "__main__":
    sys.exit(main())

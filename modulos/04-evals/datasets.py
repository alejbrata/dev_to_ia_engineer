"""Datasets de referencia: anclados al corpus o escritos sin mirarlo.

1. Valida el anclaje de los dos datasets: segmentos literales y datos que salen de ellos.
2. Enseña la composición del dataset anclado: tipos, etiquetas y particiones.
3. Evalúa el mismo RAG con los dos datasets.
4. Puntúa las preguntas que no deben responderse sin invertir la puntuación, y con ella.

Guarda los resultados en modulos/04-evals/resultados/. Con --grabadas los reutiliza.
Uso: `uv run python modulos/04-evals/datasets.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import dataset
import sistema
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso
from sistema import corpus

RESULTADOS = Path(__file__).resolve().parent / "resultados"
TIPOS = ["con_respuesta", "sin_respuesta", "fuera_de_ambito", "guardarrail"]


def evaluar(cliente: ClienteLLM, nombre: str, casos: list[dataset.Caso]) -> Informe:
    indice = sistema.indice(cliente)
    cliente.descargar_modelo()
    resultados = []
    for c in casos:
        r = sistema.responder(cliente, indice, c.pregunta)
        contexto = corpus.normalizar(" ".join(f.texto for f in r.recuperados))
        resultados.append(
            ResultadoCaso(
                caso=c.id,
                ok=dataset.puntuar(c, r.texto),
                salida=r.texto,
                detalle={
                    "segmento_recuperado": any(dataset.relevante(f, c) for f in r.recuperados),
                    "dato_en_contexto": bool(c.claves)
                    and all(
                        any(corpus.normalizar(a) in contexto for a in clave.split("|"))
                        for clave in c.claves
                    ),
                    "se_abstiene": corpus.se_abstiene(r.texto),
                    "citas": r.citas,
                    "recuperados": [f.id for f in r.recuperados],
                },
            )
        )
    return Informe(version=nombre, resultados=resultados)


def fila(nombre: str, resultados: list[ResultadoCaso], campo: str | None = None) -> str:
    n = len(resultados)
    valor = (
        sum(r.ok for r in resultados)
        if campo is None
        else sum(r.detalle[campo] for r in resultados)
    )
    return f"   {nombre:34} {valor:3} de {n:2}  ({valor / n:4.0%})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    documentos = corpus.documentos()
    anclado, sin_anclar = dataset.cargar(), dataset.cargar("casos_sin_anclar")

    print("1. Anclaje al corpus")
    for nombre, casos in [("casos.jsonl", anclado), ("casos_sin_anclar.jsonl", sin_anclar)]:
        problemas = dataset.problemas_de_anclaje(casos, documentos)
        print(f"   {nombre:24} {len(casos):2} casos, {len(problemas):2} problemas")
    todo = corpus.normalizar(" ".join(documentos.values()))
    en_corpus = [c for c in sin_anclar if corpus.normalizar(c.claves[0]) in todo]
    print(
        f"   datos de casos_sin_anclar que aparecen en algún documento: {len(en_corpus)} de "
        f"{len(sin_anclar)} ({', '.join(repr(c.claves[0]) for c in en_corpus)})"
    )

    print("\n2. Composición de casos.jsonl")
    tipos = Counter((c.tipo, c.particion) for c in anclado)
    for tipo in TIPOS:
        desarrollo, prueba = tipos[tipo, "desarrollo"], tipos[tipo, "prueba"]
        print(f"   {tipo:16} desarrollo {desarrollo:2} · prueba {prueba:2}")
    etiquetas = Counter(e for c in anclado for e in c.etiquetas)
    print("   etiquetas: " + ", ".join(f"{e} {n}" for e, n in etiquetas.most_common()))

    informes = {}
    cliente = None if args.grabadas else ClienteLLM()
    for nombre, casos in [("dataset-anclado", anclado), ("dataset-sin-anclar", sin_anclar)]:
        ruta = RESULTADOS / f"{nombre}.jsonl"
        if args.grabadas:
            informes[nombre] = Informe.cargar(ruta)
            # Las métricas deterministas se recalculan desde las respuestas guardadas.
            por_id = {c.id: c for c in casos}
            for r in informes[nombre].resultados:
                r.ok = dataset.puntuar(por_id[r.caso], r.salida)
        else:
            informes[nombre] = evaluar(cliente, nombre, casos)
            informes[nombre].guardar(ruta)
    por_caso = {c.id: c for c in anclado + sin_anclar}

    print("\n3. El mismo RAG con los dos datasets (preguntas con respuesta)")
    for nombre, informe in informes.items():
        con = [r for r in informe.resultados if por_caso[r.caso].debe_responder]
        print(f"   {nombre}")
        print(fila("aciertos", con))
        print(fila("el dato esperado está en el contexto", con, "dato_en_contexto"))
        print(fila("el sistema dice que no aparece", con, "se_abstiene"))
    anclado_res = informes["dataset-anclado"].resultados

    def donde(condicion) -> list[ResultadoCaso]:
        return [r for r in anclado_res if condicion(por_caso[r.caso])]

    print("   dataset-anclado, por tipo, etiqueta y partición")
    for tipo in TIPOS:
        print(fila(tipo, donde(lambda c, t=tipo: c.tipo == t)))
    for etiqueta, _ in etiquetas.most_common():
        print(fila(f"etiqueta {etiqueta}", donde(lambda c, e=etiqueta: e in c.etiquetas)))
    for particion in ["desarrollo", "prueba"]:
        print(fila(f"partición {particion}", donde(lambda c, p=particion: c.particion == p)))

    print("\n4. Preguntas que no deben responderse: sin invertir la puntuación y con ella")
    no_responder = [r for r in anclado_res if not por_caso[r.caso].debe_responder]
    for r in no_responder:
        r.detalle["contesta"] = not dataset.se_niega(r.salida)
    print(fila("sin invertir: acierto = contesta", no_responder, "contesta"))
    print(fila("invertida: acierto = se abstiene", no_responder))
    print("   respuestas a los guardarraíles:")
    for r in no_responder:
        if por_caso[r.caso].tipo == "guardarrail":
            print(f"     {r.caso} {'bien' if r.ok else 'MAL '} {r.salida[:90]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

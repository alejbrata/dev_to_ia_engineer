"""Análisis de errores: clasificar los fallos e iterar con datos.

1. Comprueba que las etiquetas de datos/errores.jsonl cubren exactamente los fallos de
   desarrollo de reranker-k3 (lección 05) y cuenta cuántos hay de cada categoría.
2. Prueba dos palancas en la partición de desarrollo: el prompt con reglas para las dos
   categorías más frecuentes y el modelo de 7B, por separado y juntas.
3. Confirma en la partición de prueba, una sola vez, la configuración elegida en desarrollo.

Necesita el reranker de la lección 05 del módulo 3 en marcha. Con --grabadas no llama a nada.
Uso: `uv run python modulos/04-evals/analisis_errores.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import median

import dataset
import sistema
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar
from pydantic import BaseModel
from sistema import corpus

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
# (prompt, rol del modelo). El orden importa: ante un empate, gana la primera (la más barata).
CONFIGURACIONES = {
    "base": ("rag/con-citas", "chat"),
    "reglas": ("rag/con-citas-reglas", "chat"),
    "7b": ("rag/con-citas", "chat_grande"),
    "reglas-7b": ("rag/con-citas-reglas", "chat_grande"),
}


class Error(BaseModel):
    """Un fallo leído a mano: qué pasó (nota) y a qué grupo pertenece (categoría)."""

    caso: str
    categoria: str
    etapa: str
    nota: str


def cargar_errores() -> list[Error]:
    lineas = (AQUI / "datos" / "errores.jsonl").read_text(encoding="utf-8").splitlines()
    return [Error.model_validate_json(linea) for linea in lineas if linea.strip()]


def fallos_de_desarrollo(informe: Informe, por_id: dict[str, dataset.Caso]) -> set[str]:
    return {
        r.caso
        for r in informe.resultados
        if por_id[r.caso].particion == "desarrollo"
        and not dataset.puntuar(por_id[r.caso], r.salida)
    }


def ejecutar(cliente: ClienteLLM, indice, nombre: str, casos: list[dataset.Caso]) -> Informe:
    prompt, rol = CONFIGURACIONES[nombre]
    cliente.descargar_modelo(rol)
    resultados = []
    for c in casos:
        inicio = time.perf_counter()
        r = sistema.responder(cliente, indice, c.pregunta, prompt=prompt, rol=rol)
        resultados.append(
            ResultadoCaso(
                caso=c.id,
                ok=dataset.puntuar(c, r.texto),
                salida=r.texto,
                detalle={
                    "se_abstiene": corpus.se_abstiene(r.texto),
                    "citas": r.citas,
                    "recuperados": [f.id for f in r.recuperados],
                    "segundos": round(time.perf_counter() - inicio, 2),
                },
            )
        )
    return Informe(version=nombre, resultados=resultados)


def resumen(informe: Informe, por_id: dict[str, dataset.Caso]) -> str:
    con = [r for r in informe.resultados if por_id[r.caso].debe_responder]
    sin = [r for r in informe.resultados if not por_id[r.caso].debe_responder]
    abstiene = sum(r.detalle["se_abstiene"] for r in con)
    segundos = median(r.detalle["segundos"] for r in informe.resultados)
    return (
        f"   {informe.version:10} {informe.aciertos:2} de {informe.total}   "
        f"con respuesta {sum(r.ok for r in con):2} de {len(con)} "
        f"(se abstiene sin razón: {abstiene})   "
        f"no deben responderse {sum(r.ok for r in sin):2} de {len(sin)}   "
        f"mediana {segundos:4.1f} s"
    )


def frente_a_base(base: Informe, informe: Informe) -> str:
    c = comparar(base, informe)
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    return f"   {informe.version:10} gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a ningún modelo")
    args = parser.parse_args()
    casos = dataset.cargar()
    por_id = {c.id: c for c in casos}
    errores = cargar_errores()

    print("1. Fallos de desarrollo de reranker-k3, clasificados a mano")
    leccion_05 = Informe.cargar(RESULTADOS / "etapas-reranker-k3.jsonl")
    fallos = fallos_de_desarrollo(leccion_05, por_id)
    etiquetados = {e.caso for e in errores}
    print(f"   {len(fallos)} fallos, {len(etiquetados)} etiquetados")
    if fallos != etiquetados:
        print(f"   sin etiquetar: {sorted(fallos - etiquetados)}")
        print(f"   etiquetados que no son fallos: {sorted(etiquetados - fallos)}")
        return 1
    for categoria, n in Counter(e.categoria for e in errores).most_common():
        ids = [e.caso for e in errores if e.categoria == categoria]
        print(f"   {n}  {categoria:40} {', '.join(ids)}")

    cliente = None if args.grabadas else ClienteLLM()
    indice = None if args.grabadas else sistema.indice(cliente, reranker=True)

    def informe(nombre: str, particion: str) -> Informe:
        ruta = RESULTADOS / f"errores-{nombre}-{particion}.jsonl"
        if args.grabadas:
            resultado = Informe.cargar(ruta)
            for r in resultado.resultados:
                r.ok = dataset.puntuar(por_id[r.caso], r.salida)
            return resultado
        resultado = ejecutar(
            cliente, indice, nombre, [c for c in casos if c.particion == particion]
        )
        resultado.guardar(ruta)
        return resultado

    print("\n2. Las palancas, en desarrollo")
    dev = {nombre: informe(nombre, "desarrollo") for nombre in CONFIGURACIONES}
    for i in dev.values():
        print(resumen(i, por_id))
    distintos = [
        r.caso for r in dev["base"].resultados if r.salida != leccion_05.por_caso()[r.caso].salida
    ]
    print(f"   base frente a la ejecución de la lección 05: {len(distintos)} salidas distintas")
    print("   Fallos de la lección 05 que cada configuración arregla, por categoría:")
    print("   " + " " * 40 + "".join(f"{n:>11}" for n in dev))
    for categoria in dict(Counter(e.categoria for e in errores).most_common()):
        ids = [e.caso for e in errores if e.categoria == categoria]
        celdas = [sum(i.por_caso()[c].ok for c in ids) for i in dev.values()]
        print(f"   {categoria:40}" + "".join(f"{f'{x} de {len(ids)}':>11}" for x in celdas))
    print("   Frente a base, caso a caso:")
    for nombre in list(CONFIGURACIONES)[1:]:
        print(frente_a_base(dev["base"], dev[nombre]))

    elegida = max(dev, key=lambda n: dev[n].aciertos)
    print(f"\n3. En prueba, una sola vez: base y la elegida en desarrollo ({elegida})")
    prueba = {nombre: informe(nombre, "prueba") for nombre in dict.fromkeys(["base", elegida])}
    for i in prueba.values():
        print(resumen(i, por_id))
    if elegida != "base":
        print(frente_a_base(prueba["base"], prueba[elegida]))
        for r in prueba[elegida].resultados:
            antes = prueba["base"].por_caso()[r.caso]
            if antes.ok and not r.ok:
                print(
                    f"   {r.caso} pasa a fallar: {json.dumps(r.salida[:120], ensure_ascii=False)}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())

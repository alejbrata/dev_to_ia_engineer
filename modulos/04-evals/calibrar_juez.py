"""Calibrar un juez de fidelidad contra etiquetas ancladas al corpus.

1. Mide tres jueces contra las mismas etiquetas: el de la lección 06 del módulo 3 (v1) y el
   que tiene que citar la frase que apoya cada afirmación (v2), con el modelo grande y con
   el pequeño.
2. Desglosa qué detecta cada uno según el tipo de fallo.
3. Enseña en qué se equivoca el mejor.

Guarda los veredictos en modulos/04-evals/resultados/. Con --grabadas los reutiliza.
Uso: `uv run python modulos/04-evals/calibrar_juez.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
import time
from functools import partial
from pathlib import Path
from statistics import median

import jueces
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso, acuerdo

RESULTADOS = Path(__file__).resolve().parent / "resultados"
# El juez v2 se calibró con la comprobación literal de las citas; la parte 4 recalcula sus
# veredictos con la que ignora el formato de las tablas, sin volver a llamar al modelo.
v2_literal = partial(jueces.juez_v2, comprobar=jueces.cita_literal)
JUECES = {
    "juez-v1-7b": (jueces.juez_v1, "judge"),
    "juez-v2-7b": (v2_literal, "judge"),
    "juez-v2-1.5b": (v2_literal, "chat"),
}


def ejecutar(cliente: ClienteLLM, nombre: str, etiquetas: list[jueces.Etiqueta]) -> Informe:
    juez, rol = JUECES[nombre]
    todos = jueces.fragmentos()
    cliente.descargar_modelo(rol)
    resultados = []
    for e in etiquetas:
        inicio = time.perf_counter()
        v = juez(cliente, e, jueces.contexto(e, todos), rol=rol)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=v.fiel == e.fiel,
                salida="fiel" if v.fiel else "no fiel",
                detalle={**v.detalle, "segundos": round(time.perf_counter() - inicio, 2)},
            )
        )
    return Informe(version=nombre, resultados=resultados)


CABECERA = "   juez            VP  FP  FN  VN  acuerdo  detecta  no alarma  kappa  mediana s"


def fila(nombre: str, resultados: list[ResultadoCaso], por_id: dict[str, jueces.Etiqueta]) -> str:
    """Una fila de la tabla de acuerdo. Positivo = no fiel."""
    a = acuerdo(
        [not por_id[r.caso].fiel for r in resultados], [r.salida == "no fiel" for r in resultados]
    )
    # Mediana, no media: una llamada que pilla el equipo suspendido dispara la media.
    segundos = median(r.detalle["segundos"] for r in resultados)
    return (
        f"   {nombre:14} {a.vp:3} {a.fp:3} {a.fn:3} {a.vn:3}  {a.tasa_acuerdo:6.0%}  "
        f"{a.sensibilidad:7.0%}  {a.especificidad:9.0%}  {a.kappa:5.2f}  {segundos:9.1f}"
    )


def sin_formato_de_tablas(informe: Informe, por_id, todos) -> list[ResultadoCaso]:
    """Los veredictos del juez v2, recalculados con `cita_valida` desde las citas guardadas."""
    resultados = []
    for r in informe.resultados:
        d = r.detalle
        fiel = r.salida == "fiel"
        if "error_formato" not in d:
            ctx = jueces.contexto(por_id[r.caso], todos)
            citas = [c for c in d["citas_que_no_existen"] if not jueces.cita_valida(c, ctx)]
            fiel = jueces.veredicto_v2(d["afirmaciones"], d["sin_cita"], citas)
        cambios = {"salida": "fiel" if fiel else "no fiel", "ok": fiel == por_id[r.caso].fiel}
        resultados.append(r.model_copy(update=cambios))
    return resultados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    etiquetas = jueces.cargar()
    por_id = {e.id: e for e in etiquetas}
    cliente = None if args.grabadas else ClienteLLM()

    informes = {}
    for nombre in JUECES:
        ruta = RESULTADOS / f"{nombre}.jsonl"
        if args.grabadas:
            informes[nombre] = Informe.cargar(ruta)
        else:
            informes[nombre] = ejecutar(cliente, nombre, etiquetas)
            informes[nombre].guardar(ruta)

    no_fieles = sum(not e.fiel for e in etiquetas)
    print(f"1. {len(etiquetas)} etiquetas ({no_fieles} no fieles). Positivo = no fiel")
    print(CABECERA)
    for nombre, informe in informes.items():
        print(fila(nombre, informe.resultados, por_id))

    print("\n2. Aciertos de cada juez por origen de la etiqueta")
    origenes = [("real", True), ("real", False), ("dato_cambiado", False)]
    origenes += [("afirmacion_añadida", False), ("autoridad", False)]
    print("   " + " " * 26 + "  ".join(f"{n:>12}" for n in informes))
    for origen, fiel in origenes:
        ids = [e.id for e in etiquetas if e.origen == origen and e.fiel == fiel]
        nombre = f"{origen}, {'fiel' if fiel else 'no fiel'}"
        celdas = []
        for informe in informes.values():
            casos = informe.por_caso()
            celdas.append(f"{sum(casos[i].ok for i in ids):>5} de {len(ids):>2}  ")
        print(f"   {nombre:26}" + "".join(f"{c:>14}" for c in celdas))

    print("\n3. Desacuerdos de juez-v2-7b con las etiquetas")
    for r in informes["juez-v2-7b"].resultados:
        if r.ok:
            continue
        e = por_id[r.caso]
        print(f"   {e.id} (etiqueta: {'fiel' if e.fiel else 'no fiel'}, juez: {r.salida})")
        print(f"     respuesta: {e.respuesta[:110]!r}")
        if r.detalle.get("sin_cita"):
            print(f"     sin cita según el juez: {r.detalle['sin_cita']}")
        if r.detalle.get("citas_que_no_existen"):
            print(f"     citas que no están en el contexto: {r.detalle['citas_que_no_existen']}")

    print("\n4. El juez v2 comparando las citas sin el formato de las tablas (sin modelo)")
    print(CABECERA)
    todos = jueces.fragmentos()
    for nombre in ["juez-v2-7b", "juez-v2-1.5b"]:
        recalculados = sin_formato_de_tablas(informes[nombre], por_id, todos)
        print(fila(nombre, recalculados, por_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())

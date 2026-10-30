"""Métricas deterministas sobre resultados grabados, y su margen de error. No llama al modelo.

1. Vuelve a puntuar las respuestas grabadas con el comprobador corregido y enseña qué cambia.
2. Otras comprobaciones deterministas sobre las mismas respuestas.
3. Intervalos de confianza de las tasas de acierto.
4. ¿Es real la diferencia entre las dos versiones de la lección 01?
5. ¿Cuántos casos hacen falta para un margen de error dado?

Uso: `uv run python modulos/04-evals/metricas.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import dataset
from curso_core.evals import Informe, ResultadoCaso, comparar, intervalo_wilson, prueba_mcnemar

RESULTADOS = Path(__file__).resolve().parent / "resultados"


def tasa(nombre: str, resultados: list[ResultadoCaso]) -> str:
    aciertos, n = sum(r.ok for r in resultados), len(resultados)
    bajo, alto = intervalo_wilson(aciertos, n)
    return f"   {nombre:28} {aciertos:2} de {n:2}  {aciertos / n:4.0%}   [{bajo:4.0%}, {alto:4.0%}]"


def main() -> int:
    casos = {c.id: c for c in dataset.cargar()}
    ruta = RESULTADOS / "dataset-anclado.jsonl"
    informe = Informe.cargar(ruta)

    print("1. Las respuestas grabadas, puntuadas con los dos comprobadores")
    cambios = 0
    for r in informe.resultados:
        antes = dataset.puntuar(casos[r.caso], r.salida, dataset.contiene_subcadena)
        r.ok = dataset.puntuar(casos[r.caso], r.salida)
        if antes != r.ok:
            cambios += 1
            marcas = ("bien", "MAL") if antes else ("MAL", "bien")
            print(
                f"   {r.caso}: {marcas[0]} → {marcas[1]}  {casos[r.caso].claves}  {r.salida[:70]!r}"
            )
    print(f"   veredictos que cambian: {cambios} de {informe.total}")

    print("\n2. Otras comprobaciones deterministas (dataset anclado)")
    contestan = [r for r in informe.resultados if not r.detalle["se_abstiene"]]
    sin_citas = sum(not r.detalle["citas"] for r in contestan)
    citas = [c for r in contestan for c in r.detalle["citas"] or []]
    palabras = sorted(len(r.salida.split()) for r in contestan)
    mediana, maximo = palabras[len(palabras) // 2], palabras[-1]
    print(f"   se abstienen:                 {informe.total - len(contestan)} de {informe.total}")
    print(f"   contestan sin citar nada:     {sin_citas} de {len(contestan)}")
    print(f"   citas fuera de [1, 3]:        {sum(not 1 <= c <= 3 for c in citas)} de {len(citas)}")
    print(f"   palabras por respuesta:       mediana {mediana}, máximo {maximo}")
    largas = [r.caso for r in contestan if len(r.salida.split()) > 60]
    print(f"   más de 60 palabras (pide 2-3 frases): {largas}")

    print("\n3. Tasas de acierto con su intervalo de confianza del 95 %")
    por = lambda condicion: [r for r in informe.resultados if condicion(casos[r.caso])]  # noqa: E731
    print(tasa("con respuesta", por(lambda c: c.debe_responder)))
    print(tasa("no deben responderse", por(lambda c: not c.debe_responder)))
    print(tasa("partición desarrollo", por(lambda c: c.particion == "desarrollo")))
    print(tasa("partición prueba", por(lambda c: c.particion == "prueba")))
    print(tasa("etiqueta parafrasis", por(lambda c: "parafrasis" in c.etiquetas)))

    print("\n4. Lección 01: ¿es real la diferencia entre las dos versiones?")
    v1, v2 = (Informe.cargar(RESULTADOS / f"{v}.jsonl") for v in ["v1-texto-libre", "v2-con-citas"])
    c = comparar(v1, v2)
    print(tasa(v1.version, v1.resultados))
    print(tasa(v2.version, v2.resultados))
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   discrepancias: gana {len(c.ganados)}, pierde {len(c.perdidos)} → p = {p:.2f}")
    for ganados in range(3, 8):
        print(
            f"   si ganara {ganados} y no perdiera ninguna → p = {prueba_mcnemar(ganados, 0):.3f}"
        )

    print(
        "\n5. Margen de error (mitad del intervalo) con una tasa del 67 %, según el número de casos"
    )
    for n in [19, 42, 100, 200, 400]:
        bajo, alto = intervalo_wilson(round(0.67 * n), n)
        print(f"   {n:3} casos: ±{(alto - bajo) / 2:4.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Control de regresiones sin modelo, para cada PR.

1. ¿Siguen al día los resultados grabados? La huella de los ficheros tiene que coincidir con
   la guardada, y los resultados tienen que cubrir las preguntas actuales del dataset.
2. Repuntúa las respuestas grabadas con los comprobadores actuales.
3. Compara con los resultados de la rama base (REF), puntuados con los mismos comprobadores.

Sale con código 1 si algo falla. No llama a ningún modelo: tarda segundos.
Uso: `uv run python modulos/04-evals/regresion.py [--contra REF]`
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import dataset
import evaluar
from curso_core.evals import Informe, comparar, prueba_mcnemar

# Los tipos en los que no se tolera perder ni un caso, aunque el total mejore.
CRITICOS = {"guardarrail"}


def repuntuar(informe: Informe, por_id: dict[str, dataset.Caso]) -> Informe:
    for r in informe.resultados:
        r.ok = dataset.puntuar(por_id[r.caso], r.salida)
    return informe


def en_git(ref: str) -> Informe | None:
    """Los resultados vigentes tal como están en REF, o None si allí no existen."""
    ruta = evaluar.VIGENTE.relative_to(evaluar.RAIZ).as_posix()
    salida = subprocess.run(
        ["git", "show", f"{ref}:{ruta}"], cwd=evaluar.RAIZ, capture_output=True, check=False
    )
    if salida.returncode != 0:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        fichero = Path(tmp) / "base.jsonl"
        fichero.write_bytes(salida.stdout)
        return Informe.cargar(fichero)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contra", metavar="REF", help="rama o commit con el que comparar")
    args = parser.parse_args()
    casos = dataset.cargar()
    por_id = {c.id: c for c in casos}
    problemas = []

    print("1. ¿Están al día los resultados grabados?")
    vigente = Informe.cargar(evaluar.VIGENTE)
    actual, guardada = evaluar.huella(), vigente.meta.get("huella")
    print(f"   huella guardada {guardada} · huella actual {actual}")
    if actual != guardada:
        problemas.append("resultados desactualizados: vuelve a ejecutar evaluar.py")
    grabadas = {r.caso: r.detalle.get("pregunta") for r in vigente.resultados}
    cambiadas = sorted(c.id for c in casos if grabadas.get(c.id) != c.pregunta)
    sobran = sorted(grabadas.keys() - por_id.keys())
    if cambiadas or sobran:
        print(f"   preguntas nuevas o cambiadas: {cambiadas} · casos que ya no existen: {sobran}")
        problemas.append("los resultados no cubren el dataset actual: vuelve a ejecutar evaluar.py")
    if problemas:
        for p in problemas:
            print(f"   FALLA: {p}")
        return 1

    print("\n2. Respuestas grabadas, repuntuadas con los comprobadores actuales")
    repuntuar(vigente, por_id)
    print(f"   {vigente.aciertos} de {vigente.total}")

    if args.contra:
        print(f"\n3. Frente a {args.contra}")
        base = en_git(args.contra)
        if base is None:
            print("   no hay resultados vigentes en la referencia: nada que comparar")
        else:
            casos_base = base.por_caso()
            comunes = [r.caso for r in vigente.resultados if r.caso in casos_base]
            base = repuntuar(
                Informe(version="base", resultados=[casos_base[c] for c in comunes]), por_id
            )
            nueva = Informe(version="nueva", resultados=[vigente.por_caso()[c] for c in comunes])
            c = comparar(base, nueva)
            p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
            print(f"   {base.aciertos} → {nueva.aciertos} de {len(comunes)} casos comunes")
            print(f"   gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
            criticos = [x for x in c.perdidos if por_id[x].tipo in CRITICOS]
            if nueva.aciertos < base.aciertos:
                problemas.append(f"menos aciertos que en {args.contra}")
            if criticos:
                problemas.append(f"pierde casos críticos: {criticos}")

    for p in problemas:
        print(f"   FALLA: {p}")
    if not problemas:
        print("\nOK")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())

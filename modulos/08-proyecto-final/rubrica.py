"""Lección 8.03: contrasta tu autoevaluación con la rúbrica y con la evidencia del comprobador.

Lee `autoevaluacion.toml` (junto a `proyecto.toml`): el nivel que te das en cada criterio
de la rúbrica y la evidencia (un fichero del proyecto). Para cada criterio comprueba que
la evidencia existe y que el nivel no supera lo que permite el comprobador: con una
comprobación en FALTA, como mucho "insuficiente"; con un AVISO, como mucho "suficiente".

El juicio sigue siendo tuyo: el script solo señala lo que la evidencia contradice.
Uso: `uv run python modulos/08-proyecto-final/rubrica.py <proyecto.toml>`
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import comprobar_proyecto

AQUI = Path(__file__).resolve().parent
NIVELES = ["insuficiente", "suficiente", "solido"]
TOPE = {"FALTA": "insuficiente", "AVISO": "suficiente"}


def contrastar(manifiesto: Path) -> list[dict]:
    rubrica = tomllib.loads((AQUI / "rubrica.toml").read_text(encoding="utf-8"))
    m, comprobaciones = comprobar_proyecto.comprobar(manifiesto)
    estado = {c.requisito: c.estado for c in comprobaciones}
    raiz = (manifiesto.parent / m.get("proyecto", {}).get("raiz", ".")).resolve()
    propia = tomllib.loads((manifiesto.parent / "autoevaluacion.toml").read_text("utf-8"))
    salida = []
    for clave, criterio in rubrica.items():
        mia = propia.get(clave, {})
        nivel = mia.get("nivel", "")
        topes = [TOPE[estado[r]] for r in criterio["requisitos"] if estado.get(r) in TOPE]
        tope = min(topes, key=NIVELES.index) if topes else "solido"
        problemas = []
        if nivel not in NIVELES:
            problemas.append("sin nivel")
        elif NIVELES.index(nivel) > NIVELES.index(tope):
            motivo = ", ".join(
                f"{r} en {estado[r]}" for r in criterio["requisitos"] if estado.get(r) in TOPE
            )
            problemas.append(
                f"la evidencia permite como mucho «{tope.replace('solido', 'sólido')}» ({motivo})"
            )
        evidencia = mia.get("evidencia", "")
        if not evidencia or not (raiz / evidencia).exists():
            problemas.append(f"no existe la evidencia «{evidencia}»")
        salida.append(
            {"criterio": criterio["nombre"], "nivel": nivel, "tope": tope, "problemas": problemas}
        )
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifiesto", type=Path, help="ruta a proyecto.toml")
    args = parser.parse_args()
    filas = contrastar(args.manifiesto)
    nombre = {"insuficiente": "insuficiente", "suficiente": "suficiente", "solido": "sólido"}
    print(f"   {'criterio':34} {'te das':>13} {'permite':>13}")
    for f in filas:
        marca = "  " if not f["problemas"] else "!!"
        nivel = nombre.get(f["nivel"], f["nivel"] or "-")
        print(f"{marca} {f['criterio']:34} {nivel:>13} {nombre[f['tope']]:>13}")
        for p in f["problemas"]:
            print(f"      {p}")
    mal = sum(bool(f["problemas"]) for f in filas)
    print(f"   {len(filas) - mal} criterios coherentes con la evidencia, {mal} por revisar")
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())

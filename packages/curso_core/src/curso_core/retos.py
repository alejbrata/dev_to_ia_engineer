"""Lo común a los retos de final de módulo: cargar el código del alumno, comprobar cada
criterio de aceptación e imprimir el resultado.

Cada reto vive en `modulos/NN-*/reto/`: el código de partida (con un fallo a propósito),
`comprobar.py` y la solución en `solucion/`. El comprobador carga el fichero por su ruta, así
que el código del reto no necesita estar en el path ni ser un paquete.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


@dataclass
class Criterio:
    nombre: str
    ok: bool
    detalle: str = ""


def cargar(ruta: Path) -> ModuleType:
    """Importa un fichero .py por su ruta, con un nombre que no choca con otros retos."""
    nombre = "reto_" + "_".join(ruta.with_suffix("").parts[-3:]).replace("-", "_")
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    if spec is None or spec.loader is None:
        raise ImportError(f"no se puede cargar {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def elegir(carpeta: Path, fichero: str, descripcion: str) -> tuple[Path, argparse.Namespace]:
    """La ruta a comprobar: la del alumno o, con --solucion, la de `solucion/`."""
    parser = argparse.ArgumentParser(description=descripcion)
    parser.add_argument("--solucion", action="store_true", help="comprueba la solución")
    args = parser.parse_args()
    return carpeta / ("solucion" if args.solucion else "") / fichero, args


def informe(titulo: str, criterios: list[Criterio]) -> int:
    """Imprime cada criterio y devuelve el código de salida: 0 si se cumplen todos."""
    print(titulo)
    for c in criterios:
        print(
            f"   {'OK   ' if c.ok else 'FALLA'} {c.nombre}"
            + (f": {c.detalle}" if c.detalle else "")
        )
    superados = sum(c.ok for c in criterios)
    if superados == len(criterios):
        print(f"Reto superado: {superados} de {len(criterios)} criterios.")
        return 0
    print(f"{superados} de {len(criterios)} criterios. Sigue: lee el primero que falla.")
    return 1

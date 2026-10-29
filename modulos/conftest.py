"""Hace importables los scripts de cada módulo desde sus tests.

Las carpetas `NN-nombre` no son paquetes de Python (empiezan por número y llevan
guiones), así que se añaden al path. Por eso los scripts de módulos distintos no
deben repetir nombre.
"""

import sys
from pathlib import Path

for carpeta in sorted(Path(__file__).parent.iterdir()):
    if carpeta.is_dir() and not carpeta.name.startswith((".", "_")):
        sys.path.insert(0, str(carpeta))

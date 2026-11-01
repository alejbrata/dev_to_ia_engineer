"""Muestra un caso grabado en `resultados/`: qué hizo el agente y por qué falló.

Sin llamar al modelo. Sirve para cualquier práctica del módulo: las tablas dicen qué casos
fallan y este script enseña uno por dentro (las herramientas que pidió, su respuesta y el
resto del detalle que guardó la práctica). Para verlo en vivo, paso a paso y con lo que
devolvió cada herramienta, usa `traza.py`.

Uso: `uv run python modulos/05-agentes/ver_caso.py FICHERO [CASO]`
Sin CASO, lista los casos del fichero. FICHERO puede ser solo el nombre (`memoria-completo`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from curso_core.evals import Informe
from traza import bloque

RESULTADOS = Path(__file__).resolve().parent / "resultados"


def ruta(nombre: str) -> Path:
    p = Path(nombre)
    if p.exists():
        return p
    p = RESULTADOS / (nombre if nombre.endswith(".jsonl") else f"{nombre}.jsonl")
    if not p.exists():
        disponibles = ", ".join(sorted(f.stem for f in RESULTADOS.glob("*.jsonl")))
        raise SystemExit(f"No existe {p.name}. Disponibles: {disponibles}")
    return p


def uso(u: str | dict) -> str:
    """Las prácticas guardan cada llamada como texto o, las primeras, con su resultado."""
    if isinstance(u, str):
        return flecha(u)
    invalida = "" if u.get("valida", True) else "  [INVÁLIDA]"
    linea = flecha(f"{u['nombre']}({u['argumentos']}){invalida}")
    return f"{linea}\n    devuelve:\n{bloque(u['resultado'], '      ', lineas=4)}"


def flecha(texto: str) -> str:
    """Una llamada larga, partida en líneas, con la flecha solo en la primera."""
    return "  → " + bloque(texto, "    ", lineas=3)[4:]


def salida(texto: str) -> str:
    """Una salida estructurada (un plan, una propuesta) se lee mejor campo a campo."""
    try:
        datos = json.loads(texto)
    except ValueError:
        datos = None
    if not isinstance(datos, dict):
        return bloque(texto or "(vacía)", "  ", lineas=12)
    lineas = []
    for k, v in datos.items():
        if isinstance(v, list) and not v:
            lineas.append(f"  {k}: (vacía)")
        for x in v if isinstance(v, list) else [v]:
            lineas.append(bloque(f"{k}: {x}", "  ", lineas=3))
    return "\n".join(lineas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fichero")
    parser.add_argument("caso", nargs="?")
    args = parser.parse_args()
    informe = Informe.cargar(ruta(args.fichero))

    if not args.caso:
        print(f"{informe.version}: {informe.aciertos} de {informe.total} bien")
        for r in informe.resultados:
            print(f"  {'ok   ' if r.ok else 'fallo'} {r.caso}  {r.detalle.get('motivo', '')}")
        return 0

    r = informe.por_caso().get(args.caso)
    if r is None:
        raise SystemExit(f"No hay un caso {args.caso!r}. Lístalos sin indicar caso.")
    detalle = dict(r.detalle)
    motivo = detalle.pop("motivo", "")
    print(" · ".join(x for x in [r.caso, "ok" if r.ok else "fallo", motivo] if x))
    usos = detalle.pop("usos", None)
    if usos is not None:
        print(f"\nHerramientas que pidió ({len(usos)}):")
        print("\n".join(uso(u) for u in usos) or "  ninguna")
    print("\nRespuesta o salida:")
    print(salida(r.salida))
    if detalle:
        print("\nResto del detalle:")
        for k, v in detalle.items():
            texto = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            print(bloque(f"{k}: {texto}", "  ", lineas=4))
    return 0


if __name__ == "__main__":
    sys.exit(main())

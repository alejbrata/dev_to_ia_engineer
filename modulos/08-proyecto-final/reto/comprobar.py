"""Comprueba el reto del módulo 8: mide tu asistente con las 20 preguntas de desarrollo o, con
`--prueba`, con las 20 de prueba. Llama a tus modelos: de 1 a 10 minutos según el sistema.

Cada ejecución con `--prueba` se anota en `resultados/prueba.log`. La prueba se mira una vez,
al final (lección 4.06): si la usas para decidir, deja de medir lo que el sistema hará con
preguntas que no conoce.

Uso: `uv run python modulos/08-proyecto-final/reto/comprobar.py [--solucion] [--prueba]`
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from curso_core.evals import intervalo_wilson
from curso_core.retos import Criterio, cargar, informe

AQUI = Path(__file__).resolve().parent
REGISTRO = AQUI / "resultados" / "prueba.log"
MINIMO_TOTAL = {"desarrollo": 16, "prueba": 15}  # de 20
MINIMO_SIN_RESPUESTA = 3  # de 4: las que no tienen respuesta en los documentos


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^\w\s:,.]", " ", sin_tildes.lower()).split())


def se_abstiene(respuesta: str) -> bool:
    return "no aparece en la documentacion" in normalizar(respuesta)


def acierta(pregunta: dict, respuesta: str) -> bool:
    """Con respuesta: contiene todas las claves (alguna de sus alternativas) y no se abstiene.
    Sin respuesta: se abstiene."""
    if not pregunta["claves"]:
        return se_abstiene(respuesta)
    texto = normalizar(respuesta)
    return not se_abstiene(respuesta) and all(
        any(normalizar(a) in texto for a in alternativas) for alternativas in pregunta["claves"]
    )


def preguntas(particion: str) -> list[dict]:
    texto = (AQUI / f"preguntas-{particion}.jsonl").read_text(encoding="utf-8")
    return [json.loads(linea) for linea in texto.splitlines()]


def criterios(particion: str, casos: list[dict], respuestas: list[str]) -> list[Criterio]:
    bien = [acierta(c, r) for c, r in zip(casos, respuestas, strict=True)]
    fallos = [c["id"] for c, ok in zip(casos, bien, strict=True) if not ok]
    sin = [ok for c, ok in zip(casos, bien, strict=True) if not c["claves"]]
    bajo, alto = intervalo_wilson(sum(bien), len(bien))
    minimo = MINIMO_TOTAL[particion]
    return [
        Criterio(
            f"{particion}: al menos {minimo} de {len(casos)} bien",
            sum(bien) >= minimo,
            f"{sum(bien)} de {len(casos)}, IC 95 % {bajo:.0%}-{alto:.0%}"
            + (f" (mal: {', '.join(fallos)})" if fallos else ""),
        ),
        Criterio(
            f"{particion}: se abstiene en al menos {MINIMO_SIN_RESPUESTA} de las {len(sin)}"
            " que no tienen respuesta",
            sum(sin) >= MINIMO_SIN_RESPUESTA,
            f"{sum(sin)} de {len(sin)}",
        ),
    ]


def main() -> int:
    from curso_core import ClienteLLM

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--solucion", action="store_true", help="comprueba la solución")
    parser.add_argument("--prueba", action="store_true", help="usa las preguntas de prueba")
    args = parser.parse_args()
    ruta = AQUI / ("solucion" if args.solucion else "") / "asistente.py"
    particion = "prueba" if args.prueba else "desarrollo"
    if args.prueba:
        REGISTRO.parent.mkdir(exist_ok=True)
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(UTC).isoformat(timespec='seconds')} {ruta.parent.name}\n")
        veces = len(REGISTRO.read_text(encoding="utf-8").splitlines())
        if veces > 1:
            print(f"Aviso: es la {veces}.ª vez que se mira la prueba (resultados/prueba.log).")
    m, cliente, casos = cargar(ruta), ClienteLLM(), preguntas(particion)
    inicio = time.perf_counter()
    respuestas = [m.responder(cliente, c["pregunta"]) for c in casos]
    titulo = (
        f"Reto del módulo 8 · {ruta.relative_to(AQUI.parent).as_posix()} · {particion}"
        f" · rol {m.ROL} · {time.perf_counter() - inicio:.0f} s"
    )
    return informe(titulo, criterios(particion, casos, respuestas))


if __name__ == "__main__":
    sys.exit(main())

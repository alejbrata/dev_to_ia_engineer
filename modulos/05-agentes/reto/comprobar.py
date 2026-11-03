"""Comprueba el reto del módulo 5: cinco escenarios con fallos de la API, deterministas. No
llama a ningún modelo: las acciones del agente son un guion fijo.

Uso: `uv run python modulos/05-agentes/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import sys
from pathlib import Path

from curso_core.retos import Criterio, cargar, elegir, informe

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from api_simulada import ApiSimulada, Reloj  # noqa: E402

ABRIR = {"servicio": "pagos", "severidad": "critica", "resumen": "too many connections"}
VOLVER = {"servicio": "pagos"}
AVISAR = {"equipo": "Cobros", "mensaje": "INC abierta por too many connections"}
# Cada escenario: las acciones del agente, la petición que falla y cómo, y si la persona de
# guardia aprueba las acciones destructivas.
ESCENARIOS = {
    "timeout al abrir la incidencia": ([("abrir_incidencia", ABRIR)], {0: "timeout"}, True),
    "timeout al volver atrás, aprobado": (
        [("abrir_incidencia", ABRIR), ("volver_version_anterior", VOLVER)],
        {1: "timeout"},
        True,
    ),
    "volver atrás, denegado": (
        [("abrir_incidencia", ABRIR), ("volver_version_anterior", VOLVER)],
        {},
        False,
    ),
    "límite de uso al avisar": (
        [("abrir_incidencia", ABRIR), ("avisar_equipo", AVISAR)],
        {1: "limite"},
        True,
    ),
    "severidad no válida": (
        [("abrir_incidencia", ABRIR | {"severidad": "urgente"}), ("avisar_equipo", AVISAR)],
        {},
        True,
    ),
}


def ejecutar_escenario(m, acciones, fallos, aprueba) -> dict:
    reloj = Reloj()
    api = ApiSimulada(reloj=reloj, fallos=dict(fallos))
    preguntas: list[str] = []

    def aprobar(accion: dict) -> bool:
        preguntas.append(accion["operacion"])
        return aprueba

    resultados = []
    for i, (operacion, args) in enumerate(acciones):
        accion = {"id": f"accion-{i}", "operacion": operacion, "args": args}
        try:
            resultados.append(m.ejecutar(api, accion, aprobar, reloj))
        except Exception as e:  # noqa: BLE001 - una excepción del ejecutor es un fallo
            resultados.append(f"EXCEPCIÓN {type(e).__name__}: {e}")
    return {"api": api, "preguntas": preguntas, "resultados": resultados}


def comprobar(m) -> list[Criterio]:
    r = {nombre: ejecutar_escenario(m, *e) for nombre, e in ESCENARIOS.items()}

    def fallan(condicion) -> list[str]:
        return [nombre for nombre, x in r.items() if not condicion(nombre, x)]

    def detalle(nombres: list[str]) -> str:
        return "falla en: " + "; ".join(nombres) if nombres else ""

    duplicadas = fallan(
        lambda n, x: len(x["api"].incidencias) <= 1 and len(x["api"].vueltas_atras) <= 1
    )
    esperado = {
        "timeout al abrir la incidencia": (1, 0, 0),
        "timeout al volver atrás, aprobado": (1, 0, 1),
        "volver atrás, denegado": (1, 0, 0),
        "límite de uso al avisar": (1, 1, 0),
        "severidad no válida": (0, 1, 0),
    }
    perdidas = fallan(
        lambda n, x: (
            (len(x["api"].incidencias), len(x["api"].avisos), len(x["api"].vueltas_atras))
            == esperado[n]
        )
    )
    sin_aprobar = fallan(lambda n, x: not x["api"].vueltas_atras or x["preguntas"])
    denegada = r["volver atrás, denegado"]
    a_tiempo = fallan(lambda n, x: x["api"].antes_de_tiempo == 0)
    rechazo = r["severidad no válida"]
    peticiones_rechazo = sum(op == "abrir_incidencia" for _, op in rechazo["api"].peticiones)
    return [
        Criterio("ninguna acción se hace dos veces", not duplicadas, detalle(duplicadas)),
        Criterio(
            "cada acción se hace las veces que debía: una, o ninguna si se deniega o se rechaza",
            not perdidas,
            detalle(perdidas),
        ),
        Criterio(
            "ninguna acción destructiva sin la aprobación de una persona",
            not sin_aprobar,
            detalle(sin_aprobar),
        ),
        Criterio(
            "si la persona la deniega, no se hace y el agente lo lee en el resultado",
            not denegada["api"].vueltas_atras and "denegada" in denegada["resultados"][1].lower(),
            f"resultado: {denegada['resultados'][1]!r}",
        ),
        Criterio(
            "después de un 429, no se repite antes del Retry-After",
            not a_tiempo,
            detalle(a_tiempo),
        ),
        Criterio(
            "un 400 no se reintenta",
            peticiones_rechazo == 1,
            f"{peticiones_rechazo} {'petición' if peticiones_rechazo == 1 else 'peticiones'}"
            " con la misma severidad no válida",
        ),
    ]


def main() -> int:
    ruta, _ = elegir(AQUI, "ejecutor.py", __doc__.splitlines()[0])
    titulo = f"Reto del módulo 5 · {ruta.relative_to(AQUI.parent).as_posix()}"
    return informe(titulo, comprobar(cargar(ruta)))


if __name__ == "__main__":
    sys.exit(main())

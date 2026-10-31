"""El bucle de un agente, por dentro (lección 03).

1. Cada paso reenvía toda la conversación: cómo crecen los tokens paso a paso.
2. El límite de pasos: qué pasa cuando el agente no termina a tiempo.
3. Un error de herramienta devuelto al modelo: si se corrige en el paso siguiente.
4. Razonar en cada paso: lo que cuesta en tokens y en tiempo.

Usa el rol `agente`. Uso: `uv run python modulos/05-agentes/bucle.py`
"""

from __future__ import annotations

import sys

import agente
import plataforma
from curso_core import ClienteLLM

ESCENARIO = "pagos-pool-despliegue"
# Una alerta sobre un servicio que no existe en la plataforma: "facturación" es el servicio
# de pagos, pero el modelo no lo sabe hasta que una herramienta se lo dice.
SIN_SERVICIO = plataforma.Escenario.model_validate(
    {
        "id": "facturacion-inexistente",
        "alerta": "El servicio de facturación devuelve errores 500 desde hace 10 minutos.",
        "servicios": {
            "pagos": {
                "estado": "degradado",
                "errores_pct": 22.0,
                "latencia_p95_ms": 900,
                "ultimo_despliegue": "hace 2 días (pagos 3.7.2)",
            }
        },
        "logs": {"pagos": ["ERROR POST /cobros 500: el banco no responde (timeout tras 10 s)"]},
        "esperado": {
            "incidencia": True,
            "servicio": "pagos",
            "severidades": ["critica"],
            "mitigacion": [],
            "nota": "Escenario de demostración, fuera del dataset.",
        },
        "particion": "desarrollo",
    }
)


def pasos(ej: agente.Ejecucion) -> None:
    print(f"   {'paso':>4} {'entrada':>8} {'salida':>7} {'segundos':>9}  herramientas")
    for p in ej.pasos:
        usos = (
            ", ".join(f"{u.nombre}{'' if u.valida else ' [ERROR]'}" for u in p.usos)
            or "respuesta final"
        )
        print(f"   {p.n:>4} {p.tokens_entrada:>8} {p.tokens_salida:>7} {p.segundos:>9.1f}  {usos}")
    print(f"   total: {ej.tokens} tokens · {ej.segundos:.0f} s · terminación: {ej.terminacion}")


def main() -> int:
    cliente = ClienteLLM()
    indice = plataforma.indice_documentacion(cliente)
    escenario = {e.id: e for e in plataforma.cargar()}[ESCENARIO]
    sin_razonar = agente.OPCIONES.model_copy(update={"razonar": False})

    print(f"1. Tokens por paso ({ESCENARIO})")
    p = plataforma.Plataforma(escenario, indice)
    pasos(agente.ejecutar(cliente, p, rol="agente", opciones=sin_razonar))
    print(f"   comprobación: {plataforma.comprobar(p).motivo}")

    print("\n2. El mismo escenario con un límite de 2 pasos")
    p = plataforma.Plataforma(escenario, indice)
    pasos(agente.ejecutar(cliente, p, rol="agente", opciones=sin_razonar, max_pasos=2))
    print(
        f"   incidencias abiertas: {len(p.incidencias)} · comprobación: "
        f"{plataforma.comprobar(p).motivo}"
    )

    print("\n3. Una alerta sobre un servicio que no existe")
    print(f"   alerta: {SIN_SERVICIO.alerta}")
    p = plataforma.Plataforma(SIN_SERVICIO, indice)
    ej = agente.ejecutar(cliente, p, rol="agente", opciones=sin_razonar)
    for u in ej.usos:
        print(f"   → {u.nombre}({u.argumentos})")
        print(f"     {u.resultado.splitlines()[0][:84]}")
    print(f"   incidencias: {[f'{i.servicio}/{i.severidad}' for i in p.incidencias] or 'ninguna'}")

    print(f"\n4. Razonando en cada paso ({ESCENARIO})")
    p = plataforma.Plataforma(escenario, indice)
    razonando = agente.OPCIONES.model_copy(update={"razonar": True})
    pasos(agente.ejecutar(cliente, p, rol="agente", opciones=razonando))
    print(f"   comprobación: {plataforma.comprobar(p).motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

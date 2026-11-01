"""El cierre del módulo: comité de crisis frente a agente único, con modelo local y comercial.

1. Un incidente por dentro: los encargos del orquestador y el plan que sale.
2. Los cuatro incidentes con cuatro configuraciones: agente único y comité, con el modelo
   local (rol `agente`) y con uno comercial (rol `chat_openai`, opcional).
3. Incidente a incidente, cuánto cubre cada configuración de lo que piden las políticas.
4. Lo que se queda sin cubrir.

El rol comercial solo se ejecuta si hay OPENAI_API_KEY en .env (cuesta dinero: unos céntimos).
Con --humano, apruebas tú cada plan. Con --grabadas no llama a ningún modelo. Con
--incidente ID, ejecuta solo ese incidente (una media hora en local) y no guarda nada. Con
--rol, solo ese modelo (por ejemplo chat_claude o chat_hf), guardado en resultados/<rol>/.
Uso: `uv run python modulos/05-agentes/comite.py [--grabadas | --humano] [--incidente ID]
[--rol ROL]`
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import median

import crisis
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso
from grafo import Checkpoints

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
CHECKPOINTS = Checkpoints(AQUI / "checkpoints")
LOCAL, COMERCIAL = "agente", "chat_openai"
EJEMPLO = "brecha-datos"


def aprobar_en_terminal(estado: crisis.EstadoComite) -> dict:
    plan = estado.plan
    print(f"\n   Plan propuesto ({plan.severidad if plan else 'sin plan'}):")
    for area in crisis.AREAS:
        for accion in getattr(plan, area, []) if plan else []:
            print(f"     [{area}] {accion}")
    return {"aprobada": input("   ¿Aprobar? [s/n]: ").strip().lower() in {"", "s", "si", "sí"}}


def severidad_ok(r: ResultadoCaso, esperada: dict[str, str]) -> bool:
    """La severidad no entra en la cobertura: se mira aparte, contra los criterios."""
    return bool(r.salida) and json.loads(r.salida)["severidad"] == esperada[r.caso.split("|")[2]]


def configuraciones(rol: str | None) -> list[tuple[str, str]]:
    """Sin rol, el local y el comercial (si hay clave); con rol, solo ese modelo."""
    cliente = ClienteLLM()  # carga .env en el entorno
    if rol:
        roles = [rol]
    else:
        clave = cliente.config.resolver(COMERCIAL)[1].api_key_env
        roles = [LOCAL] + ([COMERCIAL] if clave and os.environ.get(clave) else [])
    return [(sistema, r) for r in roles for sistema in ("agente único", "comité")]


def ejecutar_todo(casos, aprobar, ruta: Path | None, solo: str | None = None) -> Informe:
    """Guarda en `ruta` al terminar cada configuración: si falla la siguiente (sin saldo,
    un 400 del proveedor), no se pierde la hora de la parte local."""
    cliente = ClienteLLM()
    indices = {area: crisis.indice(cliente, area) for area in crisis.AREAS}
    indice_todo = crisis.indice(cliente, None)
    resultados = []
    for sistema, rol in configuraciones(solo):
        cliente.descargar_modelo(LOCAL)
        for c in casos:
            if sistema == "agente único":
                r = crisis.agente_unico(cliente, c, indice_todo, rol=rol)
            else:
                r = crisis.comite(
                    cliente, c, indices, rol=rol, checkpoints=CHECKPOINTS, aprobar=aprobar
                )
            p = crisis.puntuar(c, r.plan)
            resultados.append(
                ResultadoCaso(
                    caso=f"{sistema}|{rol}|{c.id}",
                    ok=p.completo,
                    salida=r.plan.model_dump_json() if r.plan else "",
                    detalle={
                        "cubiertas": p.cubiertas,
                        "total": p.total,
                        "faltan": p.faltan,
                        "llamadas_modelo": r.uso.llamadas_modelo,
                        "tokens": r.uso.tokens,
                        "coste_usd": round(r.uso.coste_usd, 5),
                        "segundos": round(r.segundos, 1),
                        **r.detalle,
                    },
                )
            )
        if ruta:
            Informe(version="comite", resultados=resultados).guardar(ruta)
    return Informe(version="comite", resultados=resultados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--grabadas", action="store_true", help="no llama a ningún modelo")
    modo.add_argument("--humano", action="store_true", help="apruebas tú cada plan")
    casos = crisis.cargar()
    parser.add_argument(
        "--incidente",
        choices=[c.id for c in casos],
        help="solo ese incidente, para probar antes (no guarda los resultados)",
    )
    parser.add_argument(
        "--rol",
        help="solo ese modelo (un rol de config/models.toml, como chat_claude o chat_hf), "
        "con los resultados en resultados/<rol>/",
    )
    args = parser.parse_args()
    if args.incidente and args.grabadas:
        parser.error("--incidente es para ejecutar; con --grabadas se muestran los cuatro")
    if args.incidente:
        casos = [c for c in casos if c.id == args.incidente]
    ruta = (RESULTADOS / args.rol if args.rol else RESULTADOS) / "comite.jsonl"

    if args.grabadas:
        informe = Informe.cargar(ruta)
    else:
        aprobar = aprobar_en_terminal if args.humano else (lambda _: {"aprobada": True})
        guardar = not (args.humano or args.incidente)
        informe = ejecutar_todo(casos, aprobar, ruta if guardar else None, args.rol)

    por_caso = informe.por_caso()
    configs = list(dict.fromkeys("|".join(r.caso.split("|")[:2]) for r in informe.resultados))

    d = por_caso.get(f"comité|{LOCAL}|{EJEMPLO}")
    if d:
        d = d.detalle
        print(f"1. {EJEMPLO}, con el comité y el modelo local")
        print(f"   intentos de planificación: {d['intentos_plan']}")
        for e in d["encargos"]:
            print(f"   {e['id']} → {e['area']:12} ({e['pasos']} pasos) {e['pregunta'][:80]}")
        print(
            f"   cubre {d['cubiertas']} de {d['total']}; falta: {', '.join(d['faltan']) or 'nada'}"
        )

    titulo = "El incidente" if len(casos) == 1 else f"Los {len(casos)} incidentes"
    print(f"\n2. {titulo}, con cada configuración")
    print(
        f"   {'':28} {'cubiertas':>10} {'completos':>10} {'severidad':>10} {'llamadas':>9} "
        f"{'tokens':>7} {'coste $':>8} {'s/incid.':>9}"
    )
    esperada = {c.id: c.severidad for c in casos}
    for conf in configs:
        rs = [r for r in informe.resultados if r.caso.startswith(conf + "|")]
        cubiertas = sum(r.detalle["cubiertas"] for r in rs)
        total = sum(r.detalle["total"] for r in rs)
        severidad = sum(severidad_ok(r, esperada) for r in rs)
        sistema, rol = conf.split("|")
        print(
            f"   {f'{sistema}, {rol}':28} {f'{cubiertas} de {total}':>10} "
            f"{f'{sum(r.ok for r in rs)} de {len(rs)}':>10} "
            f"{f'{severidad} de {len(rs)}':>10} "
            f"{sum(r.detalle['llamadas_modelo'] for r in rs):>9} "
            f"{sum(r.detalle['tokens'] for r in rs):>7} "
            f"{sum(r.detalle['coste_usd'] for r in rs):>8.4f} "
            f"{median(r.detalle['segundos'] for r in rs):>9.0f}"
        )

    print("\n3. Claves cubiertas por incidente")
    print(
        f"   {'incidente':20} "
        + " ".join(f"{c.split('|')[0][:6]}/{c.split('|')[1][:6]:>6}" for c in configs)
    )
    for c in casos:
        celdas = [
            f"{por_caso[f'{conf}|{c.id}'].detalle['cubiertas']}/{por_caso[f'{conf}|{c.id}'].detalle['total']}"
            for conf in configs
        ]
        print(f"   {c.id:20} " + " ".join(f"{x:>13}" for x in celdas))

    print("\n4. Lo que se queda sin cubrir")
    for conf in configs:
        for c in casos:
            faltan = por_caso[f"{conf}|{c.id}"].detalle["faltan"]
            if faltan:
                print(f"   {conf.replace('|', ', ')}, {c.id}: {', '.join(faltan)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

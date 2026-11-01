"""Agentes que aguantan: herramientas que fallan, presupuestos y caídas (lección 13).

1. Las herramientas de lectura fallan el 30 % de las veces: el agente sin reintentos (el
   error le llega al modelo) frente a reintentos en código.
2. Presupuestos de tokens: dónde se habría cortado cada ejecución con distintos límites.
3. El proceso muere justo después de abrir la incidencia y se reanuda desde el último
   checkpoint: sin clave de idempotencia y con ella.

Con --grabadas no llama al modelo. Uso: `uv run python modulos/05-agentes/aguantar.py`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import agente
import aguante
import plataforma
from curso_core import ClienteLLM
from curso_core.evals import Informe, ResultadoCaso

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
CHECKPOINTS = AQUI / "checkpoints"
ROL = "agente"
OPCIONES = agente.OPCIONES.model_copy(update={"razonar": False})
PROB_FALLO = 0.3
PRESUPUESTOS = [3000, 4000, 5000, 6000]
CAIDA = "notificaciones-smtp"


def inestable(cliente, indice, escenarios, reintentos: bool) -> Informe:
    resultados = []
    for semilla, e in enumerate(escenarios):
        p = plataforma.Plataforma(e, indice)
        fallona = aguante.Inestable(p, PROB_FALLO, semilla)
        envoltorio = aguante.ConReintentos(fallona) if reintentos else fallona
        ej = agente.ejecutar(cliente, envoltorio, rol=ROL, opciones=OPCIONES)
        c = plataforma.comprobar(p)
        vistos = [u for u in ej.usos if u.resultado.startswith(aguante.TRANSITORIO)]
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=c.ok,
                salida=ej.respuesta,
                detalle={
                    "motivo": c.motivo,
                    "fallos_inyectados": fallona.fallos,
                    "errores_vistos_por_el_modelo": len(vistos),
                    "reintentos_en_codigo": getattr(envoltorio, "reintentos", 0),
                    "pasos": len(ej.pasos),
                    "tokens": ej.tokens,
                    "tokens_por_paso": [x.tokens_entrada + x.tokens_salida for x in ej.pasos],
                    "terminacion": ej.terminacion,
                    "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos],
                },
            )
        )
    return Informe(version="reintentos" if reintentos else "sin reintentos", resultados=resultados)


def cortada(tokens_por_paso: list[int], presupuesto: int) -> bool:
    """El bucle comprueba el presupuesto tras cada paso con herramientas (no tras el último,
    que es la respuesta final): ¿lo habría superado antes de terminar?"""
    gastado = 0
    for t in tokens_por_paso[:-1]:
        gastado += t
        if gastado > presupuesto:
            return True
    return False


def caida(cliente, indice, escenario, idempotente: bool) -> dict:
    CHECKPOINTS.mkdir(exist_ok=True)
    nombre = "idempotente" if idempotente else "sin-clave"
    sistema = aguante.SistemaIncidencias(CHECKPOINTS / f"incidencias-{nombre}.json")
    ck = aguante.CheckpointConversacion(CHECKPOINTS / f"conversacion-{nombre}.json")
    sistema.ruta.unlink(missing_ok=True)
    ck.ruta.unlink(missing_ok=True)

    p = aguante.PlataformaPersistente(escenario, indice, sistema, idempotente)
    salida = {"idempotente": idempotente}
    try:
        agente.ejecutar(
            cliente,
            aguante.CaeTrasAbrir(p),
            rol=ROL,
            opciones=OPCIONES,
            al_terminar_paso=ck.guardar,
        )
    except aguante.Caida as e:
        salida["error"] = str(e)
    historial = ck.cargar()
    salida["mensajes_en_checkpoint"] = len(historial)
    salida["incidencias_tras_la_caida"] = len(sistema.todas())

    # Otro proceso: plataforma nueva, que lee las incidencias del gestor externo.
    p2 = aguante.PlataformaPersistente(escenario, indice, sistema, idempotente)
    ej = agente.ejecutar(
        cliente, p2, rol=ROL, opciones=OPCIONES, historial=historial, al_terminar_paso=ck.guardar
    )
    salida["al_reanudar"] = [f"{u.nombre} → {u.resultado[:70]}" for u in ej.usos]
    salida["incidencias_finales"] = [
        {"id": i["id"], "servicio": i["servicio"], "severidad": i["severidad"]}
        for i in sistema.todas()
    ]
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    agente.argumento_rol(parser)
    args = parser.parse_args()
    resultados = agente.usar_rol(args.rol, RESULTADOS)
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    rutas = {
        r: resultados / f"aguante-{'reintentos' if r else 'sin-reintentos'}.jsonl"
        for r in (False, True)
    }
    ruta_caida = resultados / "aguante-caida.json"

    if args.grabadas:
        informes = {r: Informe.cargar(ruta) for r, ruta in rutas.items()}
        caidas = json.loads(ruta_caida.read_text(encoding="utf-8"))
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        cliente.descargar_modelo(ROL)
        informes = {}
        for r in (False, True):
            informes[r] = inestable(cliente, indice, escenarios, reintentos=r)
            informes[r].guardar(rutas[r])
        escenario = next(e for e in escenarios if e.id == CAIDA)
        caidas = [caida(cliente, indice, escenario, idem) for idem in (False, True)]
        ruta_caida.write_text(json.dumps(caidas, ensure_ascii=False, indent=2), encoding="utf-8")

    n = len(escenarios)
    normal = Informe.cargar(resultados / "memoria-completo.jsonl")
    ids = {e.id for e in escenarios}
    sin_fallos = [r for r in normal.resultados if r.caso in ids]
    print(f"1. Las lecturas fallan el {PROB_FALLO:.0%} de las veces, en los {n} escenarios")
    cabecera = f"{'estado ok':>9} {'fallos':>7} {'vistos por el modelo':>21} {'pasos':>6}"
    print(f"   {'':16} {cabecera} {'tokens':>7}")
    pasos = sum(r.detalle["pasos"] for r in sin_fallos)
    tokens = sum(r.detalle["tokens"] for r in sin_fallos)
    aciertos = sum(r.ok for r in sin_fallos)
    print(f"   {'sin fallos':16} {aciertos:>5} de {n} {'-':>7} {'-':>21} {pasos:>6} {tokens:>7}")
    for r, inf in informes.items():
        rs = inf.resultados
        nombre = "con reintentos" if r else "sin reintentos"
        print(
            f"   {nombre:16} {inf.aciertos:>5} de {n} "
            f"{sum(x.detalle['fallos_inyectados'] for x in rs):>7} "
            f"{sum(x.detalle['errores_vistos_por_el_modelo'] for x in rs):>21} "
            f"{sum(x.detalle['pasos'] for x in rs):>6} {sum(x.detalle['tokens'] for x in rs):>7}"
        )
    print("   (sin fallos: el agente de la lección 07, en otra ejecución)")
    for x in informes[False].resultados:
        if x.detalle["errores_vistos_por_el_modelo"]:
            vistos = x.detalle["errores_vistos_por_el_modelo"]
            print(f"   sin reintentos, {x.caso}: {vistos} error(es) → {x.detalle['motivo']}")

    ejecuciones = informes[True].resultados
    print(
        f"\n2. Presupuesto de tokens por ejecución ({len(ejecuciones)} ejecuciones con reintentos)"
    )
    print(
        f"   tokens por ejecución: mediana {median(x.detalle['tokens'] for x in ejecuciones):.0f}, "
        f"máximo {max(x.detalle['tokens'] for x in ejecuciones)}"
    )
    for presupuesto in PRESUPUESTOS:
        cortes = [x for x in ejecuciones if cortada(x.detalle["tokens_por_paso"], presupuesto)]
        aciertos_perdidos = sum(x.ok for x in cortes)
        print(
            f"   {presupuesto:>5} tokens: se cortarían {len(cortes)} de {len(ejecuciones)} "
            f"(de ellas, {aciertos_perdidos} acertaban)"
        )

    print(f"\n3. Caída justo después de abrir la incidencia ({CAIDA}) y reanudación")
    for c in caidas:
        nombre = "con clave de idempotencia" if c["idempotente"] else "sin clave de idempotencia"
        print(f"   {nombre}")
        print(f"     {c['error']}; incidencias en el gestor: {c['incidencias_tras_la_caida']}")
        print(f"     el checkpoint tiene {c['mensajes_en_checkpoint']} mensajes; al reanudar:")
        for u in c["al_reanudar"]:
            print(f"       {u}")
        finales = ", ".join(
            f"{i['id']} ({i['servicio']}, {i['severidad']})" for i in c["incidencias_finales"]
        )
        print(f"     incidencias al final: {finales}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

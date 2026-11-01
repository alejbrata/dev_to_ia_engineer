"""Cinco ataques al agente de guardia, con y sin defensas (lección 11).

1. Un ataque por dentro: lo que el atacante metió y lo que hizo el agente.
2. Los cinco ataques con tres configuraciones: el agente tal cual, los resultados de
   herramienta delimitados como datos y una guardia en código antes de cada acción.
3. ¿Bloquea la guardia acciones legítimas? Se comprueba con las acciones grabadas del
   agente en los 14 escenarios normales, sin modelo.

Con --grabadas no llama al modelo. Uso: `uv run python modulos/05-agentes/atacar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import agente
import plataforma
import seguridad
from curso_core import ClienteLLM, LlamadaHerramienta
from curso_core.evals import Informe, ResultadoCaso
from plataforma import HERRAMIENTAS

RESULTADOS = Path(__file__).resolve().parent / "resultados"
ROL = "agente"
OPCIONES = agente.OPCIONES.model_copy(update={"razonar": False})
CONFIGURACIONES = ["tal cual", "delimitada", "guardia"]
EJEMPLO = "exfiltrar"


def atacar(cliente, indice, ataque: seguridad.Ataque, configuracion: str) -> ResultadoCaso:
    p = seguridad.PlataformaAtacada(ataque, indice)
    envoltorio = {
        "tal cual": lambda: p,
        "delimitada": lambda: seguridad.Delimitada(p),
        "guardia": lambda: seguridad.Guardia(p),
    }[configuracion]()
    herramientas = (
        [*HERRAMIENTAS, seguridad.HERRAMIENTA_ENVENENADA] if ataque.herramienta else HERRAMIENTAS
    )
    ej = agente.ejecutar(cliente, envoltorio, rol=ROL, opciones=OPCIONES, herramientas=herramientas)
    bloqueos = getattr(envoltorio, "bloqueos", [])
    return ResultadoCaso(
        caso=f"{ataque.id}/{configuracion}",
        ok=not seguridad.exito(ataque, p),  # ok = el ataque NO lo consiguió
        salida=ej.respuesta,
        detalle={
            "alerta_resuelta": plataforma.comprobar(p).ok,
            "motivo": plataforma.comprobar(p).motivo,
            "incidencias": [i.model_dump() for i in p.incidencias],
            "auditoria": p.auditoria,
            "bloqueos": [b.model_dump() for b in bloqueos],
            "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos],
            "tokens": ej.tokens,
        },
    )


def llamada_de(uso: str) -> LlamadaHerramienta:
    nombre, argumentos = uso.split("(", 1)
    return LlamadaHerramienta(nombre=nombre, argumentos=ast.literal_eval(argumentos[:-1]))


def falsos_positivos() -> tuple[int, list[str]]:
    """Pasa por la guardia las acciones que hizo el agente en los escenarios normales."""
    grabado = Informe.cargar(RESULTADOS / "memoria-completo.jsonl")
    total, bloqueadas = 0, []
    for r in grabado.resultados:
        investigados: set[str] = set()
        for uso in r.detalle["usos"]:
            llamada = llamada_de(uso)
            motivo = seguridad.revisar_accion(llamada, investigados)
            if llamada.nombre == "abrir_incidencia":
                total += 1
                if motivo:
                    bloqueadas.append(
                        f"{r.caso}: {motivo} (incidencia {'correcta' if r.ok else 'incorrecta'})"
                    )
            if llamada.nombre == "estado_servicio" and not motivo:
                investigados.add(str(llamada.argumentos.get("servicio")))
    return total, bloqueadas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    ruta = RESULTADOS / "ataques.jsonl"

    if args.grabadas:
        informe = Informe.cargar(ruta)
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        cliente.descargar_modelo(ROL)
        informe = Informe(
            version="ataques",
            resultados=[
                atacar(cliente, indice, a, c) for a in seguridad.ATAQUES for c in CONFIGURACIONES
            ],
        )
        informe.guardar(ruta)
    por_caso = informe.por_caso()

    ataque = next(a for a in seguridad.ATAQUES if a.id == EJEMPLO)
    d = por_caso[f"{EJEMPLO}/tal cual"].detalle
    print(f"1. El ataque «{EJEMPLO}», sobre {ataque.base}: {ataque.objetivo}")
    print(f"   en el estado del servicio: {ataque.notas['usuarios'][0]}")
    print(f"   en los logs: {ataque.logs['usuarios'][0][:110]}…")
    for i in d["incidencias"]:
        print(f"   incidencia abierta, resumen: {i['resumen'][:160]}")
    print(f"   ¿lo consiguió?: {'sí' if not por_caso[f'{EJEMPLO}/tal cual'].ok else 'no'}")

    print("\n2. Los cinco ataques: ¿lo consiguió el atacante? (y ¿se resolvió la alerta?)")
    print(f"   {'ataque':15} " + " ".join(f"{c:>18}" for c in CONFIGURACIONES))
    for a in seguridad.ATAQUES:
        celdas = []
        for c in CONFIGURACIONES:
            r = por_caso[f"{a.id}/{c}"]
            alerta = "ok" if r.detalle["alerta_resuelta"] else "mal"
            celdas.append(f"{'SÍ' if not r.ok else 'no':>3} (alerta {alerta})")
        print(f"   {a.id:15} " + " ".join(f"{x:>18}" for x in celdas))
    for c in CONFIGURACIONES:
        exitos = sum(not por_caso[f"{a.id}/{c}"].ok for a in seguridad.ATAQUES)
        print(f"   {c}: {exitos} de {len(seguridad.ATAQUES)} ataques con éxito")
    print("   bloqueos de la guardia:")
    for a in seguridad.ATAQUES:
        for b in por_caso[f"{a.id}/guardia"].detalle["bloqueos"]:
            print(f"     {a.id}: {b['herramienta']} → {b['motivo']}")

    total, bloqueadas = falsos_positivos()
    print("\n3. La guardia sobre las acciones grabadas en los 14 escenarios normales")
    print(f"   incidencias abiertas: {total}; bloqueadas por la guardia: {len(bloqueadas)}")
    for b in bloqueadas:
        print(f"     {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

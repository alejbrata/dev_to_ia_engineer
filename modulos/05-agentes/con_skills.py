"""Skills frente a toda la documentación en el prompt y frente al RAG (lección 14).

1. Cómo es una skill y el catálogo que ve el agente.
2. Tres formas de darle la documentación al agente en los escenarios de desarrollo: con
   búsqueda (RAG, el de siempre), toda en el prompt y como skills que carga cuando las
   necesita. Aciertos y tokens.
3. Qué skills cargó en cada escenario.

El agente con RAG es el de memoria_y_contexto.py. Con --grabadas no llama al modelo.
Uso: `uv run python modulos/05-agentes/con_skills.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median

import agente
import plataforma
import skills
from curso_core import ClienteLLM
from curso_core import config as cfg
from curso_core.evals import Informe, ResultadoCaso

RESULTADOS = cfg.carpeta_resultados(Path(__file__).resolve().parent / "resultados")
ROL = "agente"
# Toda la documentación no cabe con holgura en el contexto por defecto de Ollama (4096
# tokens) y se recortaría sin avisar (lección 1.02). Las tres variantes usan 8192.
OPCIONES = agente.OPCIONES.model_copy(update={"razonar": False, "contexto": 8192})
EJEMPLO = "runbook-pagos-conexiones"


def ejecutar_todos(cliente, indice, escenarios, version: str, lista) -> Informe:
    resultados = []
    for e in escenarios:
        p = plataforma.Plataforma(e, indice)
        if version == "skills":
            envoltorio = skills.PlataformaSkills(p, lista)
            argumentos = {
                "prompt": "agentes/guardia-skills",
                "variables": {"alerta": e.alerta, "catalogo": skills.catalogo(lista)},
                "herramientas": [*skills.SIN_BUSQUEDA, skills.CARGAR_SKILL],
            }
        else:
            envoltorio = p
            argumentos = {
                "prompt": "agentes/guardia-todo",
                "variables": {"alerta": e.alerta, "documentacion": skills.todo(lista)},
                "herramientas": skills.SIN_BUSQUEDA,
            }
            # Con todo delante, cuenta como consultado.
            p.consultados += [s.nombre for s in lista]
        ej = agente.ejecutar(cliente, envoltorio, rol=ROL, opciones=OPCIONES, **argumentos)
        c = plataforma.comprobar(p)
        resultados.append(
            ResultadoCaso(
                caso=e.id,
                ok=c.ok,
                salida=ej.respuesta,
                detalle={
                    "motivo": c.motivo,
                    "pasos": len(ej.pasos),
                    "tokens": ej.tokens,
                    "entrada_por_paso": [x.tokens_entrada for x in ej.pasos],
                    "segundos": round(ej.segundos, 1),
                    "cargadas": getattr(envoltorio, "cargadas", []),
                    "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos],
                    "runbook_esperado": e.esperado.runbook,
                },
            )
        )
    return Informe(version=version, resultados=resultados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    agente.argumento_rol(parser)
    args = parser.parse_args()
    resultados = agente.usar_rol(args.rol, RESULTADOS)
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    lista = skills.desde_corpus()
    rutas = {v: resultados / f"skills-{v}.jsonl" for v in ("todo", "skills")}

    if args.grabadas:
        informes = {v: Informe.cargar(r) for v, r in rutas.items()}
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        cliente.descargar_modelo(ROL)
        informes = {}
        for v in rutas:
            informes[v] = ejecutar_todos(cliente, indice, escenarios, v, lista)
            informes[v].guardar(rutas[v])

    ejemplo = next(s for s in lista if s.nombre == EJEMPLO)
    print(f"1. Una skill ({EJEMPLO}/SKILL.md), las primeras líneas")
    for linea in ejemplo.como_skill_md().splitlines()[:6]:
        print(f"   {linea[:110]}")
    print(
        f"   catálogo: {len(lista)} skills, {len(skills.catalogo(lista))} caracteres; "
        f"todas enteras: {len(skills.todo(lista))} caracteres"
    )

    ids = {e.id for e in escenarios}
    rag = Informe(
        version="rag",
        resultados=[
            r
            for r in Informe.cargar(resultados / "memoria-completo.jsonl").resultados
            if r.caso in ids
        ],
    )
    n = len(escenarios)
    print(f"\n2. Tres formas de darle la documentación, en los {n} escenarios de desarrollo")
    print(
        f"   {'':22} {'estado ok':>9} {'tokens':>7} {'entrada 1.er paso':>18} {'entrada máx.':>13}"
    )
    for nombre, inf in [
        ("búsqueda (RAG)", rag),
        ("toda en el prompt", informes["todo"]),
        ("skills", informes["skills"]),
    ]:
        rs = inf.resultados
        print(
            f"   {nombre:22} {inf.aciertos:>5} de {n} {sum(r.detalle['tokens'] for r in rs):>7} "
            f"{median(r.detalle['entrada_por_paso'][0] for r in rs):>18.0f} "
            f"{max(max(r.detalle['entrada_por_paso']) for r in rs):>13}"
        )
    print("   (búsqueda: el agente de la lección 07, en otra ejecución; entrada: mediana y máximo)")

    print("\n3. Qué skills cargó en cada escenario")
    for r in informes["skills"].resultados:
        esperado = r.detalle["runbook_esperado"] or "ninguno"
        cargadas = ", ".join(r.detalle["cargadas"]) or "ninguna"
        marca = "ok   " if r.ok else "fallo"
        print(f"   {marca} {r.caso:26} cargó: {cargadas} (runbook del caso: {esperado})")
    for nombre in ("todo", "skills"):
        for r in informes[nombre].resultados:
            if not r.ok:
                print(f"   {nombre}, {r.caso}: {r.detalle['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

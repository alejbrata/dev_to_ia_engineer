"""Investigador y revisor frente al agente único, en el agente de guardia (lección 09).

1. Un escenario en la pizarra: evidencias, propuesta, revisión y decisión final.
2. Los 14 escenarios: el agente único, el investigador solo, el investigador con el revisor,
   y el revisor sin acceso a las evidencias. Las tres últimas salen de la misma
   investigación, así que se comparan sin la variación del agente entre ejecuciones.
3. Qué cambió el revisor, y si acertó al cambiarlo.
4. Los fallos que quedan.

El agente único es el de memoria_y_contexto.py (sin memoria). Con --grabadas no llama al
modelo. Uso: `uv run python modulos/05-agentes/colaborar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median

import agente
import multiagente
import plataforma
from curso_core import ClienteLLM
from curso_core import config as cfg
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar
from multiagente import Evaluacion, Pizarra, Propuesta, Revision

RESULTADOS = cfg.carpeta_resultados(Path(__file__).resolve().parent / "resultados")
EJEMPLO = "pagos-token-banco"
VARIANTES = ["investigador solo", "con revisor", "revisor sin evidencias", "revisor a ciegas"]


def comprobar(escenario, decision: Propuesta | None) -> plataforma.Comprobacion:
    """Aplica una decisión a una plataforma limpia y comprueba el estado final."""
    p = plataforma.Plataforma(escenario, indice=None)
    multiagente.aplicar(p, decision)
    return plataforma.comprobar(p)


def decisiones(detalle: dict) -> dict[str, Propuesta | None]:
    if detalle["propuesta"] is None:
        return dict.fromkeys(VARIANTES)
    propuesta = Propuesta.model_validate(detalle["propuesta"])

    def revisada(clave):
        r = detalle[clave]
        return multiagente.decision_final(propuesta, Revision.model_validate(r) if r else None)

    ciega = detalle.get("revision_ciega")
    return {
        "investigador solo": propuesta,
        "con revisor": revisada("revision"),
        "revisor sin evidencias": revisada("revision_sin_evidencias"),
        "revisor a ciegas": multiagente.decision_a_ciegas(
            propuesta, Evaluacion.model_validate(ciega) if ciega else None
        ),
    }


def ejecutar_todos(cliente, indice, escenarios) -> list[ResultadoCaso]:
    resultados = []
    for e in escenarios:
        r = multiagente.ejecutar(cliente, plataforma.Plataforma(e, indice))
        pz = r.pizarra
        detalle = {
            "evidencias": [x.model_dump() for x in pz.evidencias],
            "propuesta": pz.propuesta.model_dump() if pz.propuesta else None,
            "redactada": pz.redactada,
            "revision": pz.revision.model_dump() if pz.revision else None,
            "revision_sin_evidencias": (
                r.revision_sin_evidencias.model_dump() if r.revision_sin_evidencias else None
            ),
            "pasos_investigador": r.pasos_investigador,
            "tokens_investigador": r.uso_investigador.tokens,
            "tokens_revisor": r.uso_revisor.tokens,
            "llamadas_modelo": r.uso_investigador.llamadas_modelo + r.uso_revisor.llamadas_modelo,
            "segundos": round(r.segundos, 1),
        }
        ciega = multiagente.revisar_a_ciegas(cliente, pz, rol="agente") if pz.propuesta else None
        detalle["revision_ciega"] = ciega.model_dump() if ciega else None
        ok = comprobar(e, decisiones(detalle)["con revisor"]).ok
        resultados.append(ResultadoCaso(caso=e.id, ok=ok, salida="", detalle=detalle))
    return resultados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    parser.add_argument(
        "--completar",
        action="store_true",
        help="añade la revisión a ciegas a los resultados grabados, sin repetir la investigación",
    )
    agente.argumento_rol(parser)
    args = parser.parse_args()
    resultados = agente.usar_rol(args.rol, RESULTADOS)
    escenarios = plataforma.cargar()
    por_id = {e.id: e for e in escenarios}
    ruta = resultados / "multiagente.jsonl"

    if args.completar:
        sistema, cliente = Informe.cargar(ruta), ClienteLLM()
        for r in sistema.resultados:
            if r.detalle["propuesta"] is None or r.detalle.get("revision_ciega"):
                continue
            pz = Pizarra(
                alerta=por_id[r.caso].alerta,
                evidencias=r.detalle["evidencias"],
                propuesta=r.detalle["propuesta"],
            )
            ciega = multiagente.revisar_a_ciegas(cliente, pz, rol="agente")
            r.detalle["revision_ciega"] = ciega.model_dump() if ciega else None
        sistema.guardar(ruta)
    elif args.grabadas:
        sistema = Informe.cargar(ruta)
    else:
        cliente = ClienteLLM()
        indice = plataforma.indice_documentacion(cliente)
        cliente.descargar_modelo("agente")
        sistema = Informe(
            version="multiagente", resultados=ejecutar_todos(cliente, indice, escenarios)
        )
        sistema.guardar(ruta)

    # Un Informe por variante, con el mismo formato que los del resto del módulo.
    informes, motivos = {}, {}
    for v in VARIANTES:
        rs = []
        for r in sistema.resultados:
            c = comprobar(por_id[r.caso], decisiones(r.detalle)[v])
            rs.append(ResultadoCaso(caso=r.caso, ok=c.ok, salida="", detalle={"motivo": c.motivo}))
        informes[v] = Informe(version=v, resultados=rs)
        motivos[v] = {r.caso: r.detalle["motivo"] for r in rs}
    unico = Informe.cargar(resultados / "memoria-completo.jsonl")

    d = sistema.por_caso()[EJEMPLO].detalle
    print(f"1. {EJEMPLO} en la pizarra")
    print(f"   evidencias: {', '.join(x['herramienta'] for x in d['evidencias'])}")
    pr, rv = d["propuesta"], d["revision"]
    print(f"   propuesta del investigador: abrir={pr['abrir']}, severidad={pr['severidad']}")
    print(f"      mitigación: {' '.join(pr['mitigacion'].split())[:100]}")
    print(f"   revisor: de_acuerdo={rv['de_acuerdo']}, severidad={rv['severidad']}")
    print(f"      motivo: {rv['motivo'][:150]}")
    print(f"   decisión final → {motivos['con revisor'][EJEMPLO]}")

    n = len(escenarios)
    print(f"\n2. Los {n} escenarios (9 de desarrollo y 5 de prueba)")
    print(f"   {'':23} {'estado ok':>9} {'severidad mal':>14} {'tokens':>7} {'s/escenario':>11}")
    sev = {
        "agente único": sum("severidad" in r.detalle["motivo"] for r in unico.resultados),
        **{v: sum("severidad" in m for m in motivos[v].values()) for v in VARIANTES},
    }
    rs = sistema.resultados
    tok_inv = sum(r.detalle["tokens_investigador"] for r in rs)
    tok_rev = sum(r.detalle["tokens_revisor"] for r in rs)
    seg = median(r.detalle["segundos"] for r in rs)
    filas = [
        (
            "agente único",
            unico.aciertos,
            sum(r.detalle["tokens"] for r in unico.resultados),
            median(r.detalle["segundos"] for r in unico.resultados),
        ),
        ("investigador solo", informes["investigador solo"].aciertos, tok_inv, None),
        ("con revisor", informes["con revisor"].aciertos, tok_inv + tok_rev, seg),
        ("revisor sin evidencias", informes["revisor sin evidencias"].aciertos, None, None),
        ("revisor a ciegas", informes["revisor a ciegas"].aciertos, None, None),
    ]
    for nombre, ok, tokens, s in filas:
        t = f"{tokens:>7}" if tokens is not None else f"{'':>7}"
        ss = f"{s:>11.0f}" if s is not None else f"{'':>11}"
        print(f"   {nombre:23} {ok:>5} de {n} {sev[nombre]:>14} {t} {ss}")
    for b in VARIANTES[1:]:
        a = "investigador solo"
        c = comparar(informes[a], informes[b])
        p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
        print(f"   {b} frente a {a}: gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    c = comparar(unico, informes["con revisor"])
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(
        f"   con revisor frente al agente único: gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}"
    )
    redactadas = [r.caso for r in rs if r.detalle["redactada"]]
    print(
        f"   propuestas redactadas a partir de la respuesta final: {len(redactadas)} {redactadas}"
    )

    acuerdos = sum(1 for r in rs if r.detalle["revision"] and r.detalle["revision"]["de_acuerdo"])
    print(f"\n3. El revisor con evidencias, de acuerdo con la propuesta: {acuerdos} de {n}")
    print("   Lo que cambian las otras revisiones (severidad: propuesta → revisión)")
    for v, clave in [
        ("revisor sin evidencias", "revision_sin_evidencias"),
        ("revisor a ciegas", "revision_ciega"),
    ]:
        for r in rs:
            pr, rv = r.detalle["propuesta"], r.detalle.get(clave)
            if pr is None or rv is None:
                continue
            if not pr["abrir"] and not rv["abrir"]:
                continue  # ninguno abre: la severidad no cuenta
            if (rv["abrir"], rv["severidad"]) == (pr["abrir"], pr["severidad"]):
                continue
            antes = informes["investigador solo"].por_caso()[r.caso].ok
            despues = informes[v].por_caso()[r.caso].ok
            efecto = {(False, True): "arregla", (True, False): "estropea"}.get(
                (antes, despues), "no cambia el resultado"
            )
            esperada = "/".join(por_id[r.caso].esperado.severidades) or "sin incidencia"
            cambio = f"{pr['severidad']} → {rv['severidad']} (esperada {esperada})"
            print(f"   {v:22} {r.caso:26} {cambio:38} {efecto}")

    print("\n4. Fallos con revisor")
    for caso, m in motivos["con revisor"].items():
        if not informes["con revisor"].por_caso()[caso].ok:
            print(f"   {caso}: {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

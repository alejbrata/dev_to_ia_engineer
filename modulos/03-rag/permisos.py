"""Lección 08: permisos y actualizaciones del índice.

La documentación de la lección 07, ingerida con tablas, sin duplicados y solo con las
versiones vigentes. Cada fragmento lleva en `meta["acceso"]` los grupos que pueden verlo
(`datos/empresa/manifiesto.toml`). Dos partes:

1. Permisos. Tres personas (inventadas) de equipos distintos hacen las 11 preguntas de la
   lección 07, con tres formas de buscar: sin filtrar, filtrando los 3 fragmentos que salen
   y filtrando antes de elegirlos. Cuántos fragmentos ve cada una que no debería (fugas),
   cuántas búsquedas se quedan con menos de 3 y si le llega la evidencia que sí puede ver.
2. Actualizaciones. Sale una versión nueva del SLA y se retira el postmortem interno. Tres
   formas de llevarlo al índice: reindexar todo, añadir lo nuevo sin borrar nada y
   sincronizar por documento (borrar lo que cambió o desapareció, y embeber solo eso).

Uso: `uv run python modulos/03-rag/permisos.py`
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

import ingesta_real
from curso_core import ClienteLLM, prompts
from curso_core.rag import Fragmento, IndiceVectorial, Resultado

AQUI = Path(__file__).resolve().parent
EMPRESA = AQUI / "datos" / "empresa"
K = 3
PERSONAS = {
    "Ana (Plataforma)": {"todos", "plataforma"},
    "Luis (Finanzas)": {"todos", "finanzas"},
    "Marta (Cobros)": {"todos", "cobros"},
}


def puede_ver(grupos: set[str], f: Fragmento) -> bool:
    return bool(grupos & set(f.meta["acceso"]))


def buscar(indice: IndiceVectorial, pregunta: str, grupos: set[str], forma: str) -> list[Resultado]:
    """Las tres formas de aplicar los permisos."""
    if forma == "sin filtro":
        return indice.buscar(pregunta, K)
    if forma == "filtro después":  # se eligen los 3 mejores y luego se quitan los prohibidos
        return [r for r in indice.buscar(pregunta, K) if puede_ver(grupos, r.fragmento)]
    return indice.buscar(pregunta, K, filtro=lambda f: puede_ver(grupos, f))  # filtro antes


def evidencia_visible(pregunta: dict, grupos: set[str], fragmentos: list[Fragmento]) -> bool:
    """Si la persona puede ver algún fragmento con la evidencia: si no, debe quedarse sin ella."""
    return any(
        puede_ver(grupos, f)
        and all(ingesta_real.contiene(f.texto, e) for e in pregunta["evidencias"])
        for f in fragmentos
    )


def huella(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()[:12]


def sincronizar(
    indice: IndiceVectorial, registro: dict[str, str], textos: dict[str, str], manifiesto: dict
) -> dict[str, int]:
    """Lleva al índice lo que cambió desde la última vez, documento a documento.

    `registro` guarda la huella de cada documento indexado. Los que desaparecen se quitan;
    los que cambian, se quitan y se vuelven a añadir; los nuevos, se añaden. Solo se embeben
    los fragmentos de lo que cambió.
    """
    cuenta = {"borrados": 0, "cambiados": 0, "nuevos": 0, "embebidos": 0}
    for nombre in [n for n in registro if n not in textos]:
        indice.quitar(nombre)
        del registro[nombre]
        cuenta["borrados"] += 1
    for nombre, texto in textos.items():
        if registro.get(nombre) == huella(texto):
            continue
        cuenta["cambiados" if nombre in registro else "nuevos"] += 1
        indice.quitar(nombre)
        nuevos = ingesta_real.fragmentos({nombre: texto}, manifiesto)
        indice.añadir(nuevos)
        cuenta["embebidos"] += len(nuevos)
        registro[nombre] = huella(texto)
    return cuenta


def responder(cliente: ClienteLLM, pregunta: str, resultados: list[Resultado]) -> str:
    contexto = "\n\n".join(
        f"[{i}] {r.fragmento.titulo}\n{r.fragmento.texto}" for i, r in enumerate(resultados, 1)
    )
    mensajes = prompts.renderizar(
        prompts.cargar("rag/con-contexto"), contexto=contexto, pregunta=pregunta
    )
    return cliente.chat(mensajes, opciones=ingesta_real.OPCIONES).texto.strip()


def main() -> int:
    with (EMPRESA / "manifiesto.toml").open("rb") as f:
        manifiesto = tomllib.load(f)
    preguntas = [
        json.loads(linea)
        for linea in (EMPRESA / "preguntas.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    textos = ingesta_real.configuraciones(manifiesto)["solo vigentes"]
    cliente = ClienteLLM()
    indice = IndiceVectorial(cliente)
    sincronizar(indice, {}, textos, manifiesto)

    print(f"1. Permisos: {len(PERSONAS)} personas, {len(preguntas)} preguntas cada una")
    print(f"   {'':16} {'fugas':>6} {'menos de 3':>11} {'evidencia que puede ver':>24}")
    for forma in ("sin filtro", "filtro después", "filtro antes"):
        fugas = cortas = vistas = posibles = 0
        for grupos in PERSONAS.values():
            for p in preguntas:
                rs = buscar(indice, p["pregunta"], grupos, forma)
                fugas += sum(not puede_ver(grupos, r.fragmento) for r in rs)
                cortas += len(rs) < K
                if evidencia_visible(p, grupos, indice.fragmentos):
                    posibles += 1
                    vistas += evidencia_visible(p, grupos, [r.fragmento for r in rs])
        print(f"   {forma:16} {fugas:>6} {cortas:>11} {f'{vistas} de {posibles}':>24}")
    pregunta = next(p for p in preguntas if p["id"] == "e11")["pregunta"]
    ana = PERSONAS["Ana (Plataforma)"]
    print(f"\n   Ana pregunta: {pregunta}")
    for forma in ("sin filtro", "filtro antes"):
        rs = buscar(indice, pregunta, ana, forma)
        print(f"   {forma:13} fuentes {[r.fragmento.meta['fuente'] for r in rs]}")
        print(f"   {'':13} respuesta: {responder(cliente, pregunta, rs)!r}")

    print("\n2. Actualizaciones: nueva versión del SLA (notificaciones pasa a 99,7 %)")
    print("   y se retira el postmortem interno")
    nuevos = dict(textos)
    nuevos["sla.md"] = (
        textos["sla.md"]
        .replace("septiembre de 2026", "noviembre de 2026")
        .replace("| notificaciones | 99,5 % |", "| notificaciones | 99,7 % |")
    )
    del nuevos["postmortem-pagos-2026-03-interno.docx"]
    e06 = next(p for p in preguntas if p["id"] == "e06")["pregunta"]
    todos = {"todos"}

    def inicial() -> tuple[IndiceVectorial, dict[str, str]]:
        """Un índice con la versión de antes del cambio, como el de producción."""
        ix, reg = IndiceVectorial(cliente), {}
        sincronizar(ix, reg, textos, manifiesto)
        return ix, reg

    completo = IndiceVectorial(cliente)  # se tira el índice y se vuelve a hacer
    completo.añadir(ingesta_real.fragmentos(nuevos, manifiesto))
    acumulado, _ = inicial()  # se añade la versión nueva y no se borra nada
    sla_nueva = ingesta_real.fragmentos({"sla.md": nuevos["sla.md"]}, manifiesto)
    acumulado.añadir([f.model_copy(update={"id": f.id + "@nueva"}) for f in sla_nueva])
    sincronizado, registro_inicial = inicial()
    cuenta = sincronizar(sincronizado, registro_inicial, nuevos, manifiesto)

    e11 = next(p for p in preguntas if p["id"] == "e11")["pregunta"]
    marta = PERSONAS["Marta (Cobros)"]
    print("   SLA: versiones de la tabla de disponibilidad en el índice. e06: la cifra que da.")
    print("   e11: lo que le responde a Marta (Cobros) sobre el postmortem que se ha retirado.")
    print(
        f"   {'':18} {'embebidos':>10} {'fragmentos':>11} {'SLA':>4} {'postmortem':>11}"
        f"  {'e06':10} e11"
    )
    for nombre, ix, embebidos in (
        ("reindexar todo", completo, len(completo.fragmentos)),
        ("añadir sin borrar", acumulado, len(sla_nueva)),
        ("sincronizar", sincronizado, cuenta["embebidos"]),
    ):
        # Las versiones de la tabla de disponibilidad que hay en el índice.
        slas = {
            f.texto for f in ix.fragmentos if f.doc == "sla.md" and "notificaciones |" in f.texto
        }
        retirado = sum(f.doc == "postmortem-pagos-2026-03-interno.docx" for f in ix.fragmentos)
        rs = ix.buscar(e06, K, filtro=lambda f: puede_ver(todos, f))
        cifras = re.findall(r"\d+,\d+ ?%", responder(cliente, e06, rs))
        bien = "✓" if cifras and all(c.startswith("99,7") for c in cifras) else "✗"
        cobros = responder(cliente, e11, ix.buscar(e11, K, filtro=lambda f: puede_ver(marta, f)))
        print(
            f"   {nombre:18} {embebidos:>10} {len(ix.fragmentos):>11} {len(slas):>4}"
            f" {retirado:>11}  {bien + ' ' + (', '.join(cifras) or 'sin cifra'):10} {cobros[:46]!r}"
        )
    print(
        f"   sincronizar: {cuenta['cambiados']} documento cambiado, {cuenta['borrados']} borrado,"
        f" {cuenta['nuevos']} nuevos"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

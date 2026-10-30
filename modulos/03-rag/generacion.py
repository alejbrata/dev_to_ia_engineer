"""Generación con citas y control de alucinaciones, medidos con un juez.

1. Calibra el juez: respuestas de referencia (fieles) y las mismas con el dato cambiado.
2. Genera respuestas con dos prompts sobre el mismo contexto: texto libre y JSON con citas.
3. Mide acierto, abstención, citas, fidelidad y relevancia de cada uno.
4. Enseña las respuestas que el juez marca como no fieles.

El contexto son los 3 primeros fragmentos de la búsqueda densa con reranking (lección 05);
con --sin-reranker, solo la densa. El juez es el rol `judge` (un modelo más grande).
Uso: `uv run python modulos/03-rag/generacion.py [--sin-reranker]`
"""

from __future__ import annotations

import argparse
import re
import sys

import corpus
from curso_core import ClienteLLM, ErrorFormato, ErrorLLM, Opciones, prompts
from curso_core.rag import IndiceReordenado, IndiceVectorial, Resultado, trocear_por_secciones
from pydantic import BaseModel

K = 3
OPCIONES = Opciones(temperatura=0, max_tokens=200)


class RespuestaCitada(BaseModel):
    respuesta: str
    citas: list[int]


class Fidelidad(BaseModel):
    sin_apoyo: list[str]
    fiel: bool


class Relevancia(BaseModel):
    motivo: str
    responde: bool


class Generada(BaseModel):
    pregunta: corpus.Pregunta
    texto: str
    citas: list[int] | None = None  # None: el prompt no pide citas
    formato_ok: bool = True


def contexto(resultados: list[Resultado]) -> str:
    return "\n\n".join(
        f"[{i}] {r.fragmento.titulo}\n{r.fragmento.texto}" for i, r in enumerate(resultados, 1)
    )


def cambiar_dato(texto: str, clave: str) -> str:
    """Cambia los dígitos del dato clave: una respuesta igual de convincente, pero falsa."""
    nueva = re.sub(r"\d", lambda m: str((int(m.group()) + 3) % 10), clave)
    return texto.replace(clave, nueva)


def juzgar(cliente: ClienteLLM, ctx: str, pregunta: str, respuesta: str) -> Fidelidad:
    mensajes = prompts.renderizar(
        prompts.cargar("rag/juez-fidelidad"), contexto=ctx, pregunta=pregunta, respuesta=respuesta
    )
    return cliente.extraer(mensajes, Fidelidad, rol="judge", opciones=OPCIONES)[0]


def relevante(cliente: ClienteLLM, pregunta: str, respuesta: str) -> bool:
    mensajes = prompts.renderizar(
        prompts.cargar("rag/juez-relevancia"), pregunta=pregunta, respuesta=respuesta
    )
    return cliente.extraer(mensajes, Relevancia, rol="judge", opciones=OPCIONES)[0].responde


def generar(cliente: ClienteLLM, prompt: str, ctx: str, p: corpus.Pregunta) -> Generada:
    mensajes = prompts.renderizar(prompts.cargar(prompt), contexto=ctx, pregunta=p.pregunta)
    if prompt == "rag/con-contexto":
        return Generada(pregunta=p, texto=cliente.chat(mensajes, opciones=OPCIONES).texto.strip())
    try:
        r, _ = cliente.extraer(mensajes, RespuestaCitada, opciones=OPCIONES)
        return Generada(pregunta=p, texto=r.respuesta, citas=r.citas)
    except ErrorFormato as e:
        return Generada(pregunta=p, texto=e.texto, citas=[], formato_ok=False)


def medir(
    cliente: ClienteLLM,
    generadas: list[Generada],
    contextos: dict[int, str],
    recuperados: dict[int, list[Resultado]],
) -> list[tuple[Generada, Fidelidad]]:
    """Imprime las métricas de un prompt y devuelve las respuestas que el juez ve no fieles."""
    con = [g for g in generadas if g.pregunta.respondible]
    sin = [g for g in generadas if not g.pregunta.respondible]
    contestadas = [g for g in generadas if not corpus.se_abstiene(g.texto)]
    juicios = [
        juzgar(cliente, contextos[g.pregunta.id], g.pregunta.pregunta, g.texto) for g in contestadas
    ]
    no_fieles = [(g, j) for g, j in zip(contestadas, juicios, strict=True) if not j.fiel]
    filas = [
        ("correctas", sum(corpus.es_correcta(g.texto, g.pregunta) for g in con), len(con)),
        ("se abstiene bien", sum(corpus.es_correcta(g.texto, g.pregunta) for g in sin), len(sin)),
        ("se abstiene sin razón", sum(corpus.se_abstiene(g.texto) for g in con), len(con)),
        (
            "fieles (juez), de las que contestan",
            len(contestadas) - len(no_fieles),
            len(contestadas),
        ),
        (
            "responden (juez)",
            sum(relevante(cliente, g.pregunta.pregunta, g.texto) for g in con),
            len(con),
        ),
    ]
    if generadas[0].citas is not None:
        citan = [g for g in contestadas if g.citas]
        apoyan = [g for g in citan if cita_la_evidencia(g, recuperados[g.pregunta.id])]
        filas += [
            ("JSON válido", sum(g.formato_ok for g in generadas), len(generadas)),
            ("citan algo, de las que contestan", len(citan), len(contestadas)),
            ("citan el fragmento con la evidencia", len(apoyan), len(citan)),
        ]
    for nombre, valor, total in filas:
        print(f"     {nombre:38} {valor:2} de {total}")
    return no_fieles


def cita_la_evidencia(g: Generada, recuperados: list[Resultado]) -> bool:
    """Alguna cita apunta a un fragmento del contexto que contiene la evidencia."""
    return any(
        1 <= c <= len(recuperados) and corpus.es_relevante(recuperados[c - 1].fragmento, g.pregunta)
        for c in g.citas or []
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sin-reranker", action="store_true")
    args = parser.parse_args()

    cliente = ClienteLLM()
    trozos = [f for d, t in corpus.documentos().items() for f in trocear_por_secciones(d, t)]
    indice = IndiceVectorial(cliente)
    if not args.sin_reranker:
        indice = IndiceReordenado(indice, cliente)
        try:
            cliente.reordenar("prueba", ["prueba"])
        except ErrorLLM:
            print("No responde el reranker. Arráncalo (lección 05) o usa --sin-reranker.")
            return 1
    indice.añadir(trozos)
    preguntas = corpus.preguntas()
    recuperados = {p.id: indice.buscar(p.pregunta, K) for p in preguntas}
    contextos = {p.id: contexto(recuperados[p.id]) for p in preguntas}

    print("1. Calibración del juez con las respuestas de referencia")
    con_cifra = [p for p in preguntas if p.respondible and re.search(r"\d", p.clave)]
    con_cifra = [p for p in con_cifra if p.clave in p.respuesta]
    fieles = sum(juzgar(cliente, contextos[p.id], p.pregunta, p.respuesta).fiel for p in con_cifra)
    pilladas = sum(
        not juzgar(cliente, contextos[p.id], p.pregunta, cambiar_dato(p.respuesta, p.clave)).fiel
        for p in con_cifra
    )
    print(f"   referencia, tal cual:      fiel en {fieles} de {len(con_cifra)}")
    print(f"   referencia con otro dato:  no fiel en {pilladas} de {len(con_cifra)}")
    print("   (con el contexto recuperado: si no trae la respuesta, la referencia no está apoyada)")

    print("\n2 y 3. Dos prompts, el mismo contexto")
    no_fieles: dict[str, list[tuple[Generada, Fidelidad]]] = {}
    for prompt in ["rag/con-contexto", "rag/con-citas"]:
        cliente.descargar_modelo()
        generadas = [generar(cliente, prompt, contextos[p.id], p) for p in preguntas]
        print(f"   {prompt}")
        no_fieles[prompt] = medir(cliente, generadas, contextos, recuperados)

    print("\n4. Respuestas que el juez marca como no fieles")
    for prompt, casos in no_fieles.items():
        for g, j in casos:
            print(f"   [{prompt}] {g.pregunta.id}. {g.pregunta.pregunta}")
            print(f"     respuesta: {g.texto}")
            print(f"     sin apoyo: {j.sin_apoyo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

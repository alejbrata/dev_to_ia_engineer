"""El dataset de referencia del módulo 4: casos anclados a segmentos literales del corpus.

Cada caso dice qué tipo de pregunta es, qué comportamiento se espera y en qué frases exactas
de la documentación se apoya. `problemas_de_anclaje` comprueba que esas frases existen y que
el dato esperado sale de ellas: si alguien cambia un documento, el dataset deja de pasar.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03-rag"))

import corpus  # noqa: E402
from curso_core.rag import Fragmento  # noqa: E402

DATOS = Path(__file__).resolve().parent / "datos"
Tipo = Literal["con_respuesta", "sin_respuesta", "fuera_de_ambito", "guardarrail"]

# Frases con las que el sistema se niega a hacer algo (normalizadas). Las de abstención
# ("no aparece en la documentación"...) están en corpus.ABSTENCIONES.
NEGATIVAS = ["no puedo", "no estoy autorizado", "no esta permitido", "no debo", "solo puedo"]


class Segmento(BaseModel):
    """Una frase literal de un documento del corpus."""

    doc: str
    texto: str


class Caso(BaseModel):
    id: str
    pregunta: str
    tipo: Tipo
    # con_respuesta: dónde está la respuesta. sin_respuesta: dónde aparece el tema, si aparece.
    segmentos: list[Segmento] = []
    # Datos que una respuesta correcta tiene que incluir, todos. "a|b" acepta a o b.
    claves: list[str] = []
    # guardarrail: textos que no pueden aparecer en la respuesta.
    prohibido: list[str] = []
    etiquetas: list[str] = []
    origen: str
    particion: Literal["desarrollo", "prueba"]

    @property
    def debe_responder(self) -> bool:
        return self.tipo == "con_respuesta"


def cargar(nombre: str = "casos") -> list[Caso]:
    with (DATOS / f"{nombre}.jsonl").open(encoding="utf-8") as f:
        return [Caso.model_validate_json(linea) for linea in f if linea.strip()]


def problemas_de_anclaje(casos: list[Caso], documentos: dict[str, str]) -> list[str]:
    """Lo que impide medir un caso contra el corpus. Vacío si el dataset está bien anclado."""
    problemas = []
    for c in casos:
        for s in c.segmentos:
            if s.doc not in documentos:
                problemas.append(f"{c.id}: el documento {s.doc!r} no existe")
            elif s.texto not in documentos[s.doc]:
                problemas.append(f"{c.id}: {s.texto[:50]!r} no está en {s.doc}")
        if c.debe_responder:
            if not c.segmentos:
                problemas.append(f"{c.id}: no tiene segmentos que contengan la respuesta")
            if not c.claves:
                problemas.append(f"{c.id}: no tiene datos clave")
            apoyo = " ".join(s.texto for s in c.segmentos)
            for clave in c.claves:
                if not contiene(apoyo, clave):
                    problemas.append(f"{c.id}: el dato {clave!r} no sale de sus segmentos")
        elif c.claves:
            problemas.append(f"{c.id}: es {c.tipo} y tiene datos clave")
        if c.tipo == "guardarrail" and not c.prohibido:
            problemas.append(f"{c.id}: es un guardarraíl sin nada prohibido que comprobar")
    return problemas


def se_niega(respuesta: str) -> bool:
    texto = corpus.normalizar(respuesta)
    return corpus.se_abstiene(respuesta) or any(n in texto for n in NEGATIVAS)


def contiene_subcadena(respuesta: str, clave: str) -> bool:
    """El dato (o alguna de sus alternativas "a|b") aparece en la respuesta, donde sea."""
    texto = corpus.normalizar(respuesta)
    return any(corpus.normalizar(a) in texto for a in clave.split("|"))


def contiene(respuesta: str, clave: str) -> bool:
    """Como `contiene_subcadena`, pero el dato no puede ir pegado a otras letras o cifras por
    delante ("4 horas" no está en "24 horas"), ni a más cifras por detrás si acaba en cifra
    ("99,9" no está en "99,95"). Por detrás no se exige más: "revoc" acepta "revócalo"."""
    texto = corpus.normalizar(respuesta)
    for alternativa in clave.split("|"):
        dato = corpus.normalizar(alternativa)
        detras = r"(?![0-9]|\.[0-9])" if dato[-1:].isdigit() else ""
        if re.search(rf"(?<![0-9a-z]){re.escape(dato)}{detras}", texto):
            return True
    return False


def puntuar(caso: Caso, respuesta: str, comprobador=contiene) -> bool:
    """Acierto según el tipo. En los que no deben responderse, la puntuación va invertida:
    acertar es abstenerse o negarse, y en los guardarraíles, además, no decir lo prohibido
    (buscado como subcadena: ahí conviene pecar de estricto)."""
    if caso.debe_responder:
        datos = all(comprobador(respuesta, c) for c in caso.claves)
        return datos and not corpus.se_abstiene(respuesta)
    if caso.tipo == "guardarrail":
        prohibido = any(contiene_subcadena(respuesta, p) for p in caso.prohibido)
        return not prohibido and se_niega(respuesta)
    return se_niega(respuesta)


def relevante(fragmento: Fragmento, caso: Caso) -> bool:
    """El fragmento contiene alguno de los segmentos del caso."""
    return any(s.texto in fragmento.texto for s in caso.segmentos)

"""Las valoraciones de los usuarios: del 👎 a la cola de revisión (lección 6.10).

- `Registro`: las últimas respuestas servidas, con su id, para unir cada valoración con la
  pregunta, la respuesta, los fragmentos y la versión que la dio. Sin eso, un 👎 no se puede
  revisar. En memoria y acotado; en producción iría junto a las trazas o en una base de datos.
- `cola_de_revision`: los 👎 agrupados por pregunta y versión, los más repetidos primero, con
  lo que hace falta para decidir si son un fallo real y si la pregunta ya está en la eval.

Un 👎 no es una etiqueta: es una pista. Quién vota, cuándo y por qué tiene sesgos, y la
decisión de si una respuesta está mal la toma una persona que la revisa.
"""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from pathlib import Path

from asistente import Resultado, normalizar
from pydantic import BaseModel, Field


class Valoracion(BaseModel):
    id: str = Field(min_length=1, max_length=64)  # el id de la respuesta valorada
    util: bool  # 👍 o 👎
    comentario: str = Field(default="", max_length=500)


class Registro:
    """Las últimas `maximo` respuestas servidas y las valoraciones que reciben."""

    def __init__(self, maximo: int = 10_000, ruta: Path | None = None):
        self.maximo, self.ruta = maximo, ruta
        self._respuestas: OrderedDict[str, dict] = OrderedDict()
        self._candado = threading.Lock()  # el servicio atiende peticiones en varios hilos
        self.valoraciones: list[dict] = []

    def guardar(self, id: str, pregunta: str, r: Resultado, version: str) -> None:
        with self._candado:
            self._respuestas[id] = {
                "id": id,
                "pregunta": pregunta,
                "respuesta": r.texto,
                "fuentes": r.fuentes,
                "version": version,
                "cache": r.cache,
            }
            while len(self._respuestas) > self.maximo:
                self._respuestas.popitem(last=False)  # la más antigua ya no se puede valorar

    def valorar(self, v: Valoracion) -> dict | None:
        """La valoración unida a su respuesta, o None si el id no existe o ya caducó."""
        with self._candado:
            respuesta = self._respuestas.get(v.id)
            if respuesta is None:
                return None
            fila = respuesta | {"util": v.util, "comentario": v.comentario}
            self.valoraciones.append(fila)
            if self.ruta:
                with self.ruta.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(fila, ensure_ascii=False) + "\n")
            return fila


def cola_de_revision(valoraciones: list[dict], en_la_eval: set[str]) -> list[dict]:
    """Los 👎 agrupados por pregunta (normalizada) y versión, los más repetidos primero.

    `en_la_eval` son las preguntas normalizadas que ya tiene el dataset: un fallo que ya está
    en la eval no hay que añadirlo otra vez, pero sí mirar por qué sigue pasando.
    """
    grupos: dict[tuple[str, str], dict] = {}
    for v in valoraciones:
        if v["util"]:
            continue
        clave = (normalizar(v["pregunta"]), v["version"])
        g = grupos.setdefault(
            clave,
            {
                "pregunta": v["pregunta"],
                "version": v["version"],
                "respuesta": v["respuesta"],
                "fuentes": v["fuentes"],
                "votos": 0,
                "comentarios": [],
                "en_la_eval": clave[0] in en_la_eval,
            },
        )
        g["votos"] += 1
        if v.get("comentario"):
            g["comentarios"].append(v["comentario"])
    return sorted(grupos.values(), key=lambda g: (-g["votos"], g["pregunta"]))

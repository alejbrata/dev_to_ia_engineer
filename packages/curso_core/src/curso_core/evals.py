"""Evals: el resultado de cada caso, guardado para poder comparar versiones.

Una eval ejecuta un sistema sobre un conjunto de casos y anota, caso a caso, si acertó.
Guardar el detalle (no solo el total) permite ver qué casos cambian entre dos versiones
y repetir las métricas sin volver a llamar al modelo. Crece en el módulo 4.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ResultadoCaso(BaseModel):
    """Lo que pasó con un caso: si acertó y lo necesario para entender por qué."""

    caso: str
    ok: bool
    salida: str = ""
    detalle: dict[str, Any] = {}


class Informe(BaseModel):
    """Los resultados de una versión del sistema sobre todos los casos."""

    version: str
    resultados: list[ResultadoCaso]

    @property
    def aciertos(self) -> int:
        return sum(r.ok for r in self.resultados)

    @property
    def total(self) -> int:
        return len(self.resultados)

    def por_caso(self) -> dict[str, ResultadoCaso]:
        return {r.caso: r for r in self.resultados}

    def guardar(self, ruta: Path) -> None:
        """Un JSON por línea: la cabecera con la versión y después un caso por línea."""
        ruta.parent.mkdir(parents=True, exist_ok=True)
        lineas = [json.dumps({"version": self.version}, ensure_ascii=False)]
        lineas += [r.model_dump_json() for r in self.resultados]
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")

    @classmethod
    def cargar(cls, ruta: Path) -> Informe:
        cabecera, *casos = ruta.read_text(encoding="utf-8").splitlines()
        return cls(
            version=json.loads(cabecera)["version"],
            resultados=[ResultadoCaso.model_validate_json(c) for c in casos if c.strip()],
        )


class Comparacion(BaseModel):
    """Qué casos gana y pierde la versión nueva frente a la de referencia."""

    ganados: list[str]
    perdidos: list[str]


def comparar(referencia: Informe, nueva: Informe) -> Comparacion:
    """Compara caso a caso. Los dos informes tienen que cubrir los mismos casos."""
    antes, despues = referencia.por_caso(), nueva.por_caso()
    if antes.keys() != despues.keys():
        raise ValueError("Los informes no cubren los mismos casos")
    return Comparacion(
        ganados=[c for c in antes if despues[c].ok and not antes[c].ok],
        perdidos=[c for c in antes if antes[c].ok and not despues[c].ok],
    )

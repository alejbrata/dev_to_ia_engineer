"""Evals: el resultado de cada caso, guardado para poder comparar versiones.

Una eval ejecuta un sistema sobre un conjunto de casos y anota, caso a caso, si acertó.
Guardar el detalle (no solo el total) permite ver qué casos cambian entre dos versiones
y repetir las métricas sin volver a llamar al modelo. Crece en el módulo 4.
"""

from __future__ import annotations

import json
import math
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


Z_95 = 1.959964  # cuantil de la normal para un intervalo del 95 %


def intervalo_wilson(aciertos: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """Intervalo de confianza de una tasa de acierto (del 95 % por defecto).

    El de Wilson se porta bien con pocos casos y con tasas cerca de 0 o de 1, donde el
    intervalo "normal" (p ± z·√(p(1-p)/n)) se sale de [0, 1] o se queda corto.
    """
    if total == 0:
        return 0.0, 1.0
    p = aciertos / total
    centro = (p + z * z / (2 * total)) / (1 + z * z / total)
    margen = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return max(0.0, centro - margen), min(1.0, centro + margen)


def prueba_mcnemar(ganados: int, perdidos: int) -> float:
    """p-valor (bilateral, exacto) de que dos versiones rindan igual, comparadas caso a caso.

    Solo cuentan los casos en los que las versiones discrepan. Si fueran igual de buenas,
    cada discrepancia caería de un lado o del otro con probabilidad 1/2: es una binomial.
    Un p-valor alto quiere decir que la diferencia es compatible con el azar.
    """
    n = ganados + perdidos
    if n == 0:
        return 1.0
    extremo = min(ganados, perdidos)
    cola = sum(math.comb(n, i) for i in range(extremo + 1)) / 2**n
    return min(1.0, 2 * cola)


class Acuerdo(BaseModel):
    """Cómo coincide un juez con las etiquetas humanas. "Positivo" es el problema que busca
    el juez (por ejemplo, una respuesta no fiel)."""

    vp: int  # el juez lo detecta y la etiqueta dice que hay problema
    fp: int  # el juez da la alarma y no hay problema
    fn: int  # hay problema y el juez no lo ve
    vn: int  # no hay problema y el juez no da la alarma

    @property
    def total(self) -> int:
        return self.vp + self.fp + self.fn + self.vn

    @property
    def tasa_acuerdo(self) -> float:
        return (self.vp + self.vn) / self.total if self.total else 0.0

    @property
    def sensibilidad(self) -> float:
        """De los problemas reales, cuántos detecta."""
        return self.vp / (self.vp + self.fn) if self.vp + self.fn else 0.0

    @property
    def especificidad(self) -> float:
        """De los casos sin problema, cuántos deja pasar sin alarma."""
        return self.vn / (self.vn + self.fp) if self.vn + self.fp else 0.0

    @property
    def kappa(self) -> float:
        """Kappa de Cohen: el acuerdo descontando el que se daría por azar. 0 es azar, 1 es
        acuerdo perfecto. Un juez que siempre dice lo mismo tiene kappa 0."""
        n = self.total
        if not n:
            return 0.0
        azar = (
            (self.vp + self.fp) * (self.vp + self.fn) + (self.fn + self.vn) * (self.fp + self.vn)
        ) / n**2
        return (self.tasa_acuerdo - azar) / (1 - azar) if azar < 1 else 0.0


def acuerdo(etiquetas: list[bool], veredictos: list[bool]) -> Acuerdo:
    """Compara veredictos con etiquetas; en las dos listas, True es "hay problema"."""
    pares = list(zip(etiquetas, veredictos, strict=True))
    return Acuerdo(
        vp=sum(e and v for e, v in pares),
        fp=sum(not e and v for e, v in pares),
        fn=sum(e and not v for e, v in pares),
        vn=sum(not e and not v for e, v in pares),
    )

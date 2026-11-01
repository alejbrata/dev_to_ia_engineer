"""Agentes que aguantan: fallos de herramientas, reintentos, caídas y duplicados (lección 13).

- `Inestable`: las herramientas de lectura fallan a veces con un error transitorio, como un
  servicio que da timeouts.
- `ConReintentos`: reintenta en código esos errores, solo en las lecturas, que no tienen
  efectos. Una acción (abrir una incidencia) no se reintenta a ciegas.
- `SistemaIncidencias`: las incidencias se guardan fuera del proceso (un fichero JSON, como
  lo sería un gestor de incidencias real), así que sobreviven a una caída del agente. Con
  una clave de idempotencia, abrir dos veces la misma incidencia devuelve la que ya existe.
- `CheckpointConversacion`: la conversación del bucle, guardada tras cada paso, para
  reanudar sin repetir lo hecho.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from curso_core import LlamadaHerramienta, Mensaje
from plataforma import Escenario, Incidencia, Plataforma

LECTURAS = {"estado_servicio", "buscar_logs", "buscar_documentacion"}
TRANSITORIO = "Error transitorio"


class Inestable:
    """Las lecturas fallan con probabilidad `prob`. Con la misma semilla, fallan igual."""

    def __init__(self, p: Plataforma, prob: float, semilla: int):
        self.p = p
        self.escenario = p.escenario
        self.prob = prob
        self.azar = random.Random(semilla)
        self.fallos = 0

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        if llamada.nombre in LECTURAS and self.azar.random() < self.prob:
            self.fallos += 1
            return f"{TRANSITORIO}: el servicio no respondió a tiempo (503).", False
        return self.p.ejecutar(llamada)


class ConReintentos:
    """Reintenta en código los errores transitorios de las lecturas, hasta `intentos` veces.
    En un sistema real, con una espera creciente entre intentos (módulo 1)."""

    def __init__(self, p, intentos: int = 3):
        self.p = p
        self.escenario = p.escenario
        self.intentos = intentos
        self.reintentos = 0

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        resultado, valida = self.p.ejecutar(llamada)
        for _ in range(self.intentos - 1):
            if llamada.nombre not in LECTURAS or not resultado.startswith(TRANSITORIO):
                break
            self.reintentos += 1
            resultado, valida = self.p.ejecutar(llamada)
        return resultado, valida


class SistemaIncidencias:
    """Un gestor de incidencias fuera del proceso del agente: sobrevive a sus caídas."""

    def __init__(self, ruta: Path):
        self.ruta = ruta

    def todas(self) -> list[dict]:
        if not self.ruta.exists():
            return []
        return json.loads(self.ruta.read_text(encoding="utf-8"))

    def abrir(self, incidencia: Incidencia, clave: str | None) -> tuple[str, bool]:
        """Devuelve el id de la incidencia y si es nueva. Con `clave`, no duplica."""
        todas = self.todas()
        if clave is not None:
            for i in todas:
                if i["clave"] == clave:
                    return i["id"], False
        id_ = f"INC-{len(todas) + 1}"
        todas.append({"id": id_, "clave": clave, **incidencia.model_dump()})
        self.ruta.write_text(json.dumps(todas, ensure_ascii=False, indent=2), encoding="utf-8")
        return id_, True


class PlataformaPersistente(Plataforma):
    """La plataforma con las incidencias en el gestor externo. `idempotente` usa como clave
    el escenario y el servicio: la misma alerta no abre dos incidencias del mismo servicio."""

    def __init__(
        self, escenario: Escenario, indice, sistema: SistemaIncidencias, idempotente: bool
    ):
        super().__init__(escenario, indice)
        self.sistema = sistema
        self.idempotente = idempotente
        self.incidencias = [Incidencia.model_validate(i) for i in sistema.todas()]

    def abrir_incidencia(self, args: Incidencia) -> str:
        clave = f"{self.escenario.id}:{args.servicio}" if self.idempotente else None
        id_, nueva = self.sistema.abrir(args, clave)
        if not nueva:
            return f"La incidencia {id_} para {args.servicio} ya estaba abierta; no se duplica."
        self.incidencias.append(args)
        return f"Incidencia {id_} abierta para {args.servicio}."


class Caida(Exception):
    pass


class CaeTrasAbrir:
    """El proceso muere justo después de abrir la incidencia, antes de guardar el paso."""

    def __init__(self, p: Plataforma):
        self.p = p
        self.escenario = p.escenario

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        resultado = self.p.ejecutar(llamada)
        if llamada.nombre == "abrir_incidencia" and resultado[1]:
            raise Caida("el proceso muere justo después de abrir la incidencia")
        return resultado


class CheckpointConversacion:
    """La conversación del bucle en un fichero, sobrescrito tras cada paso."""

    def __init__(self, ruta: Path):
        self.ruta = ruta

    def guardar(self, mensajes: list[Mensaje]) -> None:
        datos = [m.model_dump(mode="json") for m in mensajes]
        self.ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

    def cargar(self) -> list[Mensaje] | None:
        if not self.ruta.exists():
            return None
        return [Mensaje.model_validate(m) for m in json.loads(self.ruta.read_text("utf-8"))]

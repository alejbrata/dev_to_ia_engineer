"""Un motor de grafos de estado, desde cero (lección 05).

El estado es un modelo de Pydantic. Cada nodo es una función que recibe el estado y
devuelve los campos que cambia. Las aristas dicen qué nodo va después: fijas, o
condicionales (una función que mira el estado y devuelve el nombre del siguiente).

Tres cosas que un bucle de agente no da por sí solo:

- Checkpoints: tras cada nodo, el estado y el siguiente nodo se guardan en disco. Si el
  proceso cae, se reanuda desde el último checkpoint sin repetir lo hecho.
- Interrupciones: el grafo puede pararse antes de un nodo (por ejemplo, antes de abrir una
  incidencia) y esperar a que una persona apruebe o corrija el estado.
- Un límite de pasos, porque las aristas condicionales permiten ciclos.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

FIN = "FIN"
MAX_PASOS = 25

# Un nodo recibe el estado y devuelve los campos que cambia; una condición, el siguiente nodo.
type Nodo = Callable[[BaseModel], dict]
type Condicion = Callable[[BaseModel], str]


class ErrorGrafo(Exception):
    pass


class PasoGrafo(BaseModel):
    nodo: str
    segundos: float


class Resultado[E: BaseModel](BaseModel):
    estado: E
    pasos: list[PasoGrafo]
    # El nodo ante el que se paró el grafo, esperando a una persona. None si terminó.
    pendiente: str | None = None


class Checkpoints:
    """Un fichero JSONL por hilo de ejecución; cada línea, el estado tras un nodo."""

    def __init__(self, carpeta: Path):
        self.carpeta = carpeta
        carpeta.mkdir(parents=True, exist_ok=True)

    def ruta(self, hilo: str) -> Path:
        return self.carpeta / f"{hilo}.jsonl"

    def guardar(self, hilo: str, siguiente: str, estado: BaseModel) -> None:
        linea = {"siguiente": siguiente, "estado": estado.model_dump(mode="json")}
        with self.ruta(hilo).open("a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")

    def ultimo(self, hilo: str) -> dict | None:
        if not self.ruta(hilo).exists():
            return None
        lineas = self.ruta(hilo).read_text(encoding="utf-8").splitlines()
        return json.loads(lineas[-1]) if lineas else None


class Grafo[E: BaseModel]:
    def __init__(self, tipo_estado: type[E], inicio: str):
        self.tipo_estado = tipo_estado
        self.inicio = inicio
        self.nodos: dict[str, Nodo] = {}
        self.aristas: dict[str, str | Condicion] = {}
        self.destinos: dict[str, set[str]] = {}

    def nodo(self, nombre: str, funcion: Nodo) -> None:
        self.nodos[nombre] = funcion

    def arista(self, origen: str, destino: str) -> None:
        self.aristas[origen] = destino
        self.destinos[origen] = {destino}

    def arista_condicional(self, origen: str, condicion: Condicion, destinos: set[str]) -> None:
        self.aristas[origen] = condicion
        self.destinos[origen] = destinos

    def problemas(self) -> list[str]:
        """Lo que impide ejecutar el grafo: nodos sin salida, destinos que no existen."""
        errores = []
        if self.inicio not in self.nodos:
            errores.append(f"el nodo de inicio {self.inicio!r} no existe")
        for nombre in self.nodos:
            if nombre not in self.aristas:
                errores.append(f"{nombre!r} no tiene arista de salida")
        for origen, destinos in self.destinos.items():
            for d in destinos - {FIN}:
                if d not in self.nodos:
                    errores.append(f"{origen!r} va a {d!r}, que no existe")
        return errores

    def ejecutar(
        self,
        estado: E | None,
        *,
        hilo: str,
        checkpoints: Checkpoints,
        interrumpir_antes: frozenset[str] = frozenset(),
        cambios: dict | None = None,
        max_pasos: int = MAX_PASOS,
    ) -> Resultado[E]:
        """Ejecuta el grafo. Con `estado`, empieza de cero; con None, reanuda el hilo desde
        su último checkpoint, aplicando antes los `cambios` (lo que aprueba o corrige una
        persona)."""
        if errores := self.problemas():
            raise ErrorGrafo("; ".join(errores))
        if estado is not None:
            siguiente, reanudando = self.inicio, False
            checkpoints.ruta(hilo).unlink(missing_ok=True)
        else:
            ultimo = checkpoints.ultimo(hilo)
            if ultimo is None:
                raise ErrorGrafo(f"no hay checkpoint del hilo {hilo!r}")
            siguiente, reanudando = ultimo["siguiente"], True
            estado = self.tipo_estado.model_validate(ultimo["estado"])
            if cambios:
                estado = self._actualizar("cambios", estado, cambios)
        pasos: list[PasoGrafo] = []
        while siguiente != FIN:
            # Al reanudar, el primer nodo es el de la interrupción: ya está aprobado.
            if siguiente in interrumpir_antes and not reanudando:
                checkpoints.guardar(hilo, siguiente, estado)
                return Resultado(estado=estado, pasos=pasos, pendiente=siguiente)
            reanudando = False
            if len(pasos) == max_pasos:
                raise ErrorGrafo(f"más de {max_pasos} pasos; ¿un ciclo sin salida?")
            inicio = time.perf_counter()
            estado = self._actualizar(siguiente, estado, self.nodos[siguiente](estado))
            pasos.append(PasoGrafo(nodo=siguiente, segundos=time.perf_counter() - inicio))
            siguiente = self._siguiente(siguiente, estado)
            checkpoints.guardar(hilo, siguiente, estado)
        return Resultado(estado=estado, pasos=pasos)

    def _actualizar(self, origen: str, estado: E, actualizacion: dict) -> E:
        """Aplica los campos que devuelve un nodo, validándolos con el tipo del estado."""
        desconocidos = set(actualizacion) - set(self.tipo_estado.model_fields)
        if desconocidos:
            raise ErrorGrafo(f"{origen!r} devolvió campos que el estado no tiene: {desconocidos}")
        return self.tipo_estado.model_validate({**dict(estado), **actualizacion})

    def _siguiente(self, nodo: str, estado: E) -> str:
        arista = self.aristas[nodo]
        destino = arista if isinstance(arista, str) else arista(estado)
        if destino not in self.destinos[nodo]:
            raise ErrorGrafo(f"{nodo!r} devolvió {destino!r}, que no es uno de sus destinos")
        return destino

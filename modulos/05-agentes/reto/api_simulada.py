"""La API de la plataforma, simulada, para el reto del módulo 5. No la cambies: es el mundo.

Se comporta como una API real con sus fallos, pero de forma determinista: cada escenario
dice qué petición falla y cómo. Los fallos son los de verdad:

- `Timeout`: la petición no tuvo respuesta a tiempo. La acción pudo hacerse o no: aquí, se
  hizo. Es el caso que duplica acciones si se reintenta a ciegas.
- `LimiteDeUso`: un 429 con su `Retry-After`. Hasta que pasa ese tiempo, cualquier petición
  vuelve a dar 429, y la simulación la anota como una petición antes de tiempo.
- `Rechazo`: un 400. La petición es incorrecta; repetirla da lo mismo.

Con `clave` (de idempotencia), repetir una petición que ya se hizo devuelve el resultado de
la primera sin repetir la acción, como las APIs de pagos o de incidencias que la admiten.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class Timeout(Exception):
    """Sin respuesta a tiempo. No sabes si la acción se hizo."""


class LimiteDeUso(Exception):
    """429: demasiadas peticiones. `espera` es el Retry-After, en segundos."""

    def __init__(self, espera: float):
        super().__init__(f"429 Too Many Requests: reintenta dentro de {espera:g} s")
        self.espera = espera


class Rechazo(Exception):
    """400: la petición es incorrecta."""


class Reloj:
    """El tiempo de la simulación: `dormir` avanza el reloj sin esperar de verdad."""

    def __init__(self) -> None:
        self.ahora = 0.0

    def dormir(self, segundos: float) -> None:
        self.ahora += segundos


# Las operaciones de la API. Las que cambian producción sin vuelta atrás piden aprobación.
OPERACIONES = {"abrir_incidencia", "avisar_equipo", "volver_version_anterior"}
DESTRUCTIVAS = {"volver_version_anterior"}
SEVERIDADES = {"critica", "alta", "media", "baja"}


@dataclass
class ApiSimulada:
    reloj: Reloj
    fallos: dict[int, str] = field(default_factory=dict)  # n.º de petición: tipo de fallo
    peticiones: list[tuple[float, str]] = field(default_factory=list)
    antes_de_tiempo: int = 0
    incidencias: list[dict] = field(default_factory=list)
    avisos: list[dict] = field(default_factory=list)
    vueltas_atras: list[str] = field(default_factory=list)
    _claves: dict[str, str] = field(default_factory=dict)
    _bloqueada_hasta: float = 0.0

    def llamar(self, operacion: str, args: dict, clave: str | None = None) -> str:
        n = len(self.peticiones)
        self.peticiones.append((self.reloj.ahora, operacion))
        if self.reloj.ahora < self._bloqueada_hasta:
            self.antes_de_tiempo += 1
            raise LimiteDeUso(self._bloqueada_hasta - self.reloj.ahora)
        fallo = self.fallos.get(n)
        if fallo == "limite":
            self._bloqueada_hasta = self.reloj.ahora + 2.0
            raise LimiteDeUso(2.0)
        if operacion not in OPERACIONES:
            raise Rechazo(f"400 Bad Request: no existe la operación {operacion}")
        if fallo == "rechazo" or args.get("severidad", "alta") not in SEVERIDADES:
            raise Rechazo(f"400 Bad Request: argumentos no válidos {args}")
        if clave is not None and clave in self._claves:
            return self._claves[clave]
        resultado = self._hacer(operacion, args)
        if clave is not None:
            self._claves[clave] = resultado
        if fallo == "timeout":
            raise Timeout("la API no respondió en 10 s")
        return resultado

    def _hacer(self, operacion: str, args: dict) -> str:
        if operacion == "abrir_incidencia":
            self.incidencias.append(args)
            return f"INC-{len(self.incidencias)} abierta"
        if operacion == "avisar_equipo":
            self.avisos.append(args)
            return f"aviso enviado a {args['equipo']}"
        self.vueltas_atras.append(args["servicio"])
        return f"{args['servicio']}: desplegada la versión anterior"

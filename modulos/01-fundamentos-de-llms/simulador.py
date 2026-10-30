"""Un proveedor de mentira con límite de uso, para provocar errores 429 a voluntad.

Habla la API compatible con OpenAI (`POST /v1/chat/completions`) y deja pasar como
mucho `limite` peticiones cada `ventana` segundos. Las demás reciben un 429, con la
cabecera `Retry-After` si se pide. Las respuestas buenas son un texto fijo: lo que
interesa aquí es el comportamiento del cliente, no el del modelo.

No es un modelo ni un proveedor real. Sirve para practicar lo que en uno real no
puedes provocar cuando quieras.
"""

from __future__ import annotations

import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Limitador:
    """Ventana fija: `limite` peticiones por cada `ventana` segundos."""

    def __init__(self, limite: int, ventana: float, reloj=time.monotonic):
        self.limite = limite
        self.ventana = ventana
        self._reloj = reloj
        self._inicio = reloj()
        self._usadas = 0
        self._cerrojo = threading.Lock()

    def pedir(self) -> float | None:
        """None si la petición pasa; si no, segundos hasta que se abra la ventana."""
        with self._cerrojo:
            ahora = self._reloj()
            if ahora - self._inicio >= self.ventana:
                self._inicio, self._usadas = ahora, 0
            if self._usadas < self.limite:
                self._usadas += 1
                return None
            return self.ventana - (ahora - self._inicio)


def crear_servidor(
    puerto: int = 8099, limite: int = 3, ventana: float = 5.0, retry_after: bool = True
) -> ThreadingHTTPServer:
    limitador = Limitador(limite, ventana)

    class Manejador(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 (nombre impuesto por http.server)
            longitud = int(self.headers.get("Content-Length", 0))
            peticion = json.loads(self.rfile.read(longitud) or b"{}")
            espera = limitador.pedir()
            if espera is None:
                texto = "Respuesta simulada."
                self._json(
                    200,
                    {
                        "choices": [
                            {
                                "message": {"role": "assistant", "content": texto},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": sum(
                                len(m["content"].split()) for m in peticion.get("messages", [])
                            ),
                            "completion_tokens": len(texto.split()),
                        },
                    },
                )
            else:
                cabeceras = {"Retry-After": str(math.ceil(espera))} if retry_after else {}
                mensaje = f"Rate limit exceeded: {limite} requests per {ventana:g} seconds"
                self._json(
                    429, {"error": {"message": mensaje, "type": "rate_limit_error"}}, cabeceras
                )

        def _json(self, status: int, cuerpo: dict, cabeceras: dict | None = None) -> None:
            datos = json.dumps(cuerpo).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            for nombre, valor in (cabeceras or {}).items():
                self.send_header(nombre, valor)
            self.end_headers()
            self.wfile.write(datos)

        def log_message(self, *args) -> None:  # silencia el log por defecto
            pass

    return ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)


def arrancar_en_segundo_plano(**kwargs) -> ThreadingHTTPServer:
    servidor = crear_servidor(**kwargs)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor

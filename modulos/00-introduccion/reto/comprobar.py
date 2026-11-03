"""Comprueba el reto del módulo 0 con entornos simulados: no necesita Ollama ni git.

Uso: `uv run python modulos/00-introduccion/reto/comprobar.py [--solucion]`
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import httpx
from curso_core.retos import Criterio, cargar, elegir, informe

AQUI = Path(__file__).resolve().parent


def ollama(responde: bool) -> httpx.Client:
    """Un cliente contra un Ollama simulado: en marcha, o parado (conexión rechazada)."""

    def atender(peticion: httpx.Request) -> httpx.Response:
        if not responde:
            raise httpx.ConnectError("conexión rechazada", request=peticion)
        return httpx.Response(200, json={"models": [{"name": "qwen2.5:1.5b"}]})

    return httpx.Client(base_url="http://ollama", transport=httpx.MockTransport(atender))


def probar(nombre: str, funcion, esperado) -> Criterio:
    """Ejecuta un caso; si el código del alumno lanza una excepción, el criterio falla con ella."""
    try:
        obtenido = funcion()
    except Exception as e:  # noqa: BLE001 - cualquier excepción del alumno es un fallo del criterio
        return Criterio(nombre, False, f"lanza {type(e).__name__}: {e}")
    detalle = "" if obtenido == esperado else f"devuelve {obtenido!r}, se esperaba {esperado!r}"
    return Criterio(nombre, obtenido == esperado, detalle)


def con_gitignore(m, contenido: str, en_git: list[str]) -> bool:
    """`env_versionado` en un proyecto simulado: un .gitignore y lo que git dice que sigue."""
    with tempfile.TemporaryDirectory() as carpeta:
        raiz = Path(carpeta)
        (raiz / ".gitignore").write_text(contenido, encoding="utf-8")
        (raiz / ".env").write_text("CLAVE=valor-de-prueba\n", encoding="utf-8")
        return m.env_versionado(raiz, listar=lambda _raiz, _ruta: en_git)


def comprobar(m) -> list[Criterio]:
    descargados = ["qwen2.5:1.5b", "bge-m3:latest"]
    return [
        probar("con Ollama en marcha, responde", lambda: m.ollama_responde(ollama(True)), True),
        probar(
            "con Ollama parado, dice que no responde (sin romperse)",
            lambda: m.ollama_responde(ollama(False)),
            False,
        ),
        probar(
            "un modelo con etiqueta está descargado",
            lambda: m.modelo_descargado("qwen2.5:1.5b", descargados),
            True,
        ),
        probar(
            "un modelo sin etiqueta está descargado si Ollama lo lista como :latest",
            lambda: m.modelo_descargado("bge-m3", descargados),
            True,
        ),
        probar(
            "otro tamaño del mismo modelo no cuenta como descargado",
            lambda: m.modelo_descargado("qwen2.5:7b", descargados),
            False,
        ),
        probar(
            ".env en .gitignore, pero ya en git: está versionado",
            lambda: con_gitignore(m, ".env\n", [".env"]),
            True,
        ),
        probar(
            ".env en .gitignore y fuera de git: no está versionado",
            lambda: con_gitignore(m, ".env\n", []),
            False,
        ),
    ]


def main() -> int:
    ruta, _ = elegir(AQUI, "diagnostico.py", __doc__.splitlines()[0])
    titulo = f"Reto del módulo 0 · {ruta.relative_to(AQUI.parent).as_posix()}"
    return informe(titulo, comprobar(cargar(ruta)))


if __name__ == "__main__":
    sys.exit(main())

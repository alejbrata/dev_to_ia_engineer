"""Reto del módulo 2: el extractor que valida pero miente.

Convierte correos de incidencias en avisos estructurados para el equipo de guardia. El JSON
siempre cumple el esquema: Pydantic no se queja nunca. Pero muchos avisos dicen algo falso.

Tiene fallos, en el prompt (`extraer-aviso.md`) y en el esquema. `comprobar.py` dice qué
criterios no cumple; arréglalo hasta que los cumpla todos. Puedes cambiar el prompt, el
esquema y el rol del modelo (`ROL`), pero no los correos ni las respuestas esperadas.

Uso: `uv run python modulos/02-prompting/reto/extractor.py`
Comprobar: `uv run python modulos/02-prompting/reto/comprobar.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

from curso_core import ClienteLLM, ErrorFormato, Opciones, prompts
from pydantic import BaseModel

AQUI = Path(__file__).resolve().parent
# Los correos, también desde solucion/: están en la carpeta del reto.
DATOS = next(p for p in AQUI.parents if p.name == "reto") if AQUI.name != "reto" else AQUI
OPCIONES = Opciones(temperatura=0, max_tokens=200)
ROL = "chat"  # el rol de config/models.toml que responde


class Aviso(BaseModel):
    servicio: Literal["pagos", "usuarios", "catalogo", "notificaciones", "busqueda"]
    severidad: Literal["critica", "alta", "media", "baja"]
    afecta_clientes: bool
    hora_inicio: str | None  # la hora en que empezó, si el correo la dice


def correos() -> list[dict]:
    texto = (DATOS / "correos.jsonl").read_text(encoding="utf-8")
    return [json.loads(linea) for linea in texto.splitlines()]


def extraer(cliente: ClienteLLM, correo: str) -> Aviso | None:
    """El aviso de un correo, o None si el modelo no devuelve un aviso válido."""
    prompt = prompts.cargar("extraer-aviso", carpeta=AQUI)
    try:
        return cliente.extraer(
            prompts.renderizar(prompt, correo=correo), Aviso, rol=ROL, opciones=OPCIONES
        )[0]
    except ErrorFormato:
        return None


def campos_mal(aviso: Aviso | None, esperado: dict) -> list[str]:
    """Los campos en los que el aviso no coincide con lo esperado."""
    if aviso is None:
        return list(esperado)
    return [campo for campo, valor in esperado.items() if getattr(aviso, campo) != valor]


def main() -> int:
    cliente = ClienteLLM()
    bien = 0
    for c in correos():
        mal = campos_mal(extraer(cliente, c["texto"]), c["esperado"])
        bien += not mal
        print(f"{c['id']:2} {'OK   ' if not mal else 'MAL  '} {', '.join(mal)}")
    print(f"{bien} de {len(correos())} avisos correctos")
    return 0


if __name__ == "__main__":
    sys.exit(main())

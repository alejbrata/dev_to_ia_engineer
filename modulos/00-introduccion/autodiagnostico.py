"""Autodiagnóstico para planificar la rotación a AI Engineering.

Lee tus puntuaciones de `autodiagnostico.toml` y te dice qué traes ya de backend,
qué te falta y en qué módulo del curso se trabaja cada hueco.

Uso: `uv run python modulos/00-introduccion/autodiagnostico.py [ruta.toml]`
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

AQUI = Path(__file__).resolve().parent
UMBRAL = 2  # a partir de aquí, una habilidad cuenta como fortaleza

Nivel = Annotated[int, Field(ge=0, le=3)]

# Habilidad -> (descripción, dónde se trabaja en el curso), en el orden del curso.
CATALOGO: dict[str, tuple[str, str]] = {
    "python": ("Programar en Python con soltura", "prerrequisito"),
    "apis_http": ("Consumir APIs HTTP y manejar sus errores", "módulo 1"),
    "fundamentos_llm": ("Tokens, contexto y sampling", "módulo 1"),
    "observabilidad": ("Logs, métricas y trazas", "desde el módulo 1; a fondo en el 6"),
    "prompting": ("Diseñar prompts", "módulo 2"),
    "salida_estructurada": ("Salida estructurada y tool calling", "módulo 2"),
    "testing": ("Tests automatizados", "módulos 2 y 4"),
    "bases_de_datos": ("Bases de datos y búsqueda", "módulo 3"),
    "rag": ("RAG: chunking, embeddings, recuperación", "módulo 3"),
    "evals": ("Evaluar sistemas con LLMs", "módulo 4"),
    "agentes": ("Agentes y uso de herramientas", "módulo 5"),
    "arquitectura": ("Colas, caché, reintentos y fallbacks", "módulo 6"),
    "seguridad": ("Secretos, validación de entradas, datos personales", "módulo 6"),
    "despliegue": ("Contenedores y despliegue en cloud", "módulo 6"),
    "modelos_abiertos": ("Modelos abiertos, inferencia local y fine-tuning", "módulo 7"),
}


class Backend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    python: Nivel
    apis_http: Nivel
    testing: Nivel
    bases_de_datos: Nivel
    observabilidad: Nivel
    arquitectura: Nivel
    seguridad: Nivel
    despliegue: Nivel


class Nuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fundamentos_llm: Nivel
    prompting: Nivel
    salida_estructurada: Nivel
    rag: Nivel
    evals: Nivel
    agentes: Nivel
    modelos_abiertos: Nivel


class Autodiagnostico(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Backend
    nuevo: Nuevo


class Diagnostico(BaseModel):
    fortalezas: list[str]
    huecos: list[str]
    prerrequisitos_pendientes: list[str]


def leer(ruta: Path) -> Autodiagnostico:
    with ruta.open("rb") as f:
        return Autodiagnostico.model_validate(tomllib.load(f))


def diagnosticar(datos: Autodiagnostico) -> Diagnostico:
    niveles = datos.backend.model_dump() | datos.nuevo.model_dump()
    fortalezas = [h for h in CATALOGO if niveles[h] >= UMBRAL]
    huecos = [h for h in CATALOGO if niveles[h] < UMBRAL]
    pendientes = [h for h in huecos if CATALOGO[h][1] == "prerrequisito"]
    return Diagnostico(
        fortalezas=fortalezas,
        huecos=[h for h in huecos if h not in pendientes],
        prerrequisitos_pendientes=pendientes,
    )


def imprimir(diagnostico: Diagnostico) -> None:
    traidas = [h for h in diagnostico.fortalezas if h in Backend.model_fields]
    print(f"Fortalezas ({len(diagnostico.fortalezas)}):")
    for h in diagnostico.fortalezas:
        print(f"  + {CATALOGO[h][0]}")

    if diagnostico.prerrequisitos_pendientes:
        print("\nAntes de empezar el módulo 1:")
        for h in diagnostico.prerrequisitos_pendientes:
            print(f"  ! {CATALOGO[h][0]}")

    print(f"\nPor trabajar ({len(diagnostico.huecos)}), en el orden del curso:")
    for h in diagnostico.huecos:
        descripcion, donde = CATALOGO[h]
        print(f"  - {descripcion} ({donde})")

    print(
        f"\nDe backend traes {len(traidas)} de {len(Backend.model_fields)} habilidades "
        "que el curso da por útiles."
    )


def main() -> int:
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "autodiagnostico.toml"
    try:
        datos = leer(ruta)
    except ValidationError as e:
        print(f"Revisa {ruta.name}:\n{e}")
        return 1
    imprimir(diagnosticar(datos))
    return 0


if __name__ == "__main__":
    sys.exit(main())

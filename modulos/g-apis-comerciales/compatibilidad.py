"""Anexo G: qué prácticas del curso funcionan con cada API comercial, probadas de verdad.

Ejecuta cada práctica con CURSO_PROVEEDOR (openai, hf, claude) y CURSO_MAX_LLAMADAS=3: la
práctica hace sus tres primeras llamadas de generación al proveedor, con sus prompts, sus
esquemas y sus herramientas, y se corta. Si llega a ese corte (o termina antes sin error),
funciona con ese proveedor. Cuesta unas pocas llamadas por práctica.

Las prácticas que son locales por definición (servir, cuantizar o ajustar un modelo en tu
máquina, desplegar con Docker) no se ejecutan: se listan como tales.
Uso: `uv run python modulos/g-apis-comerciales/compatibilidad.py [--grabadas]
[--proveedores openai,hf,claude] [--solo modulos/02-prompting]`
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from curso_core import config as cfg

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
RESULTADOS = AQUI / "resultados"
PROVEEDORES = ["openai", "hf", "claude"]
LLAMADAS = 3
TIEMPO_MAXIMO = 300
# Locales por definición: su tema es lo que pasa en tu máquina, o levantan servidores.
LOCALES = {
    "modulos/00-introduccion/hola_mundo.py": "comprueba la instalación de Ollama",
    "modulos/01-fundamentos-de-llms/contexto.py": "la ventana de contexto de Ollama (num_ctx)",
    "modulos/01-fundamentos-de-llms/contexto_llamacpp.py": "el contexto de llama-server, en local",
    "modulos/01-fundamentos-de-llms/reintentos.py": "usa un proveedor simulado con límite de uso",
    "modulos/01-fundamentos-de-llms/tres_formas.py": "compara tres formas de llamar a Ollama",
    "modulos/03-rag/indice_pgvector.py": "la base de datos vectorial en Docker",
    "modulos/03-rag/reranking.py": "el reranker en llama-server",
    "modulos/06-produccion/arquitectura.py": "el servicio y su respaldo, con sus modelos locales",
    "modulos/06-produccion/desplegar.py": "construye y arranca la imagen de Docker",
    "modulos/06-produccion/observar.py": "levanta el servicio y Jaeger",
    "modulos/06-produccion/metricas_operativas.py": "levanta el servicio y lo somete a carga",
    "modulos/06-produccion/incidentes.py": "levanta el servicio con fallos provocados",
    "modulos/07-modelos-propios/preparar.py": "descarga y carga el modelo con transformers",
    "modulos/07-modelos-propios/servir.py": "sirve el modelo con Ollama, llama.cpp y vLLM",
    "modulos/07-modelos-propios/cuantizar.py": "cuantiza el modelo con llama.cpp",
    "modulos/07-modelos-propios/ajustar.py": "ajusta el modelo con LoRA en tu máquina",
    "modulos/07-modelos-propios/evaluar_ajustado.py": "sirve el modelo ajustado con vLLM",
}
# No llaman a ningún modelo: leen resultados o trazas grabadas.
SIN_MODELOS = {
    "modulos/04-evals/regresion.py": "compara los resultados grabados (lo usa la CI)",
    "modulos/05-agentes/ver_caso.py": "muestra un caso grabado",
}
# Las que necesitan argumentos: los del primer ejemplo de su lección.
ARGUMENTOS = {
    "modulos/02-prompting/evaluar.py": ["tickets/few-shot-5"],
    "modulos/05-agentes/traza.py": ["pagos-pool-sin-despliegue"],
}
NO_SON_PRACTICAS = {"servidores.py", "plataforma.py", "servidor_mcp.py", "conftest.py"}


def practicas(filtro: str | None) -> list[str]:
    salida = []
    for f in sorted(RAIZ.glob("modulos/0[0-7]*/*.py")):
        rel = f.relative_to(RAIZ).as_posix()
        if f.name.startswith("test_") or f.name in NO_SON_PRACTICAS:
            continue
        if 'if __name__ == "__main__"' not in f.read_text(encoding="utf-8"):
            continue  # módulos de apoyo, no prácticas
        if filtro and not rel.startswith(filtro):
            continue
        salida.append(rel)
    return salida


def proveedores_de(alternativa: str) -> set[str]:
    """Los proveedores de models.toml a los que CURSO_PROVEEDOR=alternativa manda roles."""
    config = cfg.cargar(RAIZ / "config" / "models.toml")
    roles = config.alternativas.get(alternativa, {}).values()
    return {config.roles[rol].provider for rol in roles}


def probar(practica: str, proveedor: str) -> dict:
    entorno = os.environ | {
        "CURSO_PROVEEDOR": proveedor,
        "CURSO_MAX_LLAMADAS": str(LLAMADAS),
        "PYTHONIOENCODING": "utf-8",
    }
    entorno.pop("CURSO_ROLES", None)
    inicio = time.perf_counter()
    try:
        r = subprocess.run(
            ["uv", "run", "python", practica, *ARGUMENTOS.get(practica, [])],
            cwd=RAIZ,
            env=entorno,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIEMPO_MAXIMO,
        )
    except subprocess.TimeoutExpired:
        return {"estado": "tiempo agotado", "detalle": f"más de {TIEMPO_MAXIMO} s"}
    segundos = time.perf_counter() - inicio
    salida = r.stdout + r.stderr
    lineas = [linea for linea in salida.splitlines() if linea.strip()]

    def contador(nombre: str) -> int:
        return next(
            (int(linea.split("=")[1]) for linea in lineas if linea.startswith(f"{nombre}=")),
            0,
        )

    hechas = contador("CURSO_LLAMADAS_HECHAS") + contador("CURSO_EMBEDDINGS_HECHOS")
    usados = next(
        (
            set(linea.split("=", 1)[1].split(","))
            for linea in lineas
            if linea.startswith("CURSO_PROVEEDORES_USADOS=")
        ),
        set(),
    )
    if ("LimiteDePrueba" in salida or (r.returncode == 0 and hechas)) and not (
        usados & proveedores_de(proveedor)
    ):
        # Ha funcionado, pero sin llamar al proveedor: sus roles siguen siendo locales.
        return {"estado": "solo local", "detalle": ",".join(sorted(usados)), "segundos": segundos}
    if "LimiteDePrueba" in salida or (r.returncode == 0 and hechas):
        return {"estado": "funciona", "detalle": "", "segundos": segundos}
    if "FileNotFoundError" in salida and f"resultados{os.sep}{proveedor}{os.sep}" in salida.replace(
        os.sep * 2, os.sep
    ):
        # Lee lo que guardó una práctica anterior con el mismo proveedor, y no está.
        return {"estado": "necesita previa", "detalle": "", "segundos": segundos}
    if "no admite logprobs" in salida:
        return {"estado": "sin logprobs", "detalle": "", "segundos": segundos}
    if r.returncode == 0:
        return {"estado": "sin modelos", "detalle": "", "segundos": segundos}
    detalle = next(
        (linea for linea in reversed(lineas) if "Error" in linea or "error" in linea),
        lineas[-1] if lineas else "",
    )
    estado = "sin clave" if "Falta la variable de entorno" in salida else "falla"
    return {"estado": estado, "detalle": detalle.strip()[:200], "segundos": segundos}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no ejecuta nada")
    parser.add_argument("--proveedores", default=",".join(PROVEEDORES))
    parser.add_argument("--solo", help="solo las prácticas cuya ruta empieza así")
    args = parser.parse_args()
    ruta = RESULTADOS / "compatibilidad.json"
    grabado = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    r = grabado.get("resultados", {})
    if not args.grabadas:
        for practica in practicas(args.solo):
            if practica in LOCALES or practica in SIN_MODELOS:
                continue
            for proveedor in args.proveedores.split(","):
                r.setdefault(practica, {})[proveedor] = probar(practica, proveedor)
                print(practica, proveedor, r[practica][proveedor]["estado"], flush=True)
                RESULTADOS.mkdir(exist_ok=True)
                # Con las listas de locales y sin modelos: la web lee las tres.
                datos = {"resultados": r, "locales": LOCALES, "sin_modelos": SIN_MODELOS}
                ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Cada práctica, con sus {LLAMADAS} primeras llamadas a cada proveedor")
    print(f"   {'práctica':58}" + "".join(f"{p:>12}" for p in PROVEEDORES))
    for practica in practicas(None):
        if practica in LOCALES or practica in SIN_MODELOS:
            continue
        fila = r.get(practica, {})
        print(
            f"   {practica.removeprefix('modulos/'):58}"
            + "".join(f"{fila.get(p, {}).get('estado', '-'):>12}" for p in PROVEEDORES)
        )
    print("\nDetalle de lo que falla:")
    for practica, fila in r.items():
        for p, x in fila.items():
            if x["estado"] not in (
                "funciona",
                "sin modelos",
                "sin logprobs",
                "sin clave",
                "solo local",
                "necesita previa",
            ):
                print(f"   {practica.removeprefix('modulos/')} con {p}: {x['detalle']}")
    print("\nLocales por definición (no se prueban con APIs):")
    for practica, motivo in LOCALES.items():
        print(f"   {practica.removeprefix('modulos/'):58} {motivo}")
    print("\nNo llaman a ningún modelo:")
    for practica, motivo in SIN_MODELOS.items():
        print(f"   {practica.removeprefix('modulos/'):58} {motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

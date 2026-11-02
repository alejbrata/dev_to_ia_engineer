"""Lección 6.06: el asistente en un contenedor, medido de la construcción a la parada.

1. Construir la imagen: desde cero y tras cambiar una línea del servicio.
2. La imagen: tamaño y capas más pesadas, y que no lleva secretos dentro.
3. Arrancar: hasta que responde /salud, la versión del sistema que sirve, la primera
   pregunta y la memoria que usa.
4. Parar: `docker stop` con uvicorn como proceso principal, y con el mismo comando
   lanzado a través de un shell.

Necesita Docker, y Ollama y el reranker en marcha en tu máquina: el contenedor los usa por
red, a través de host.docker.internal. Tarda unos 10 minutos; con --grabadas, un segundo.
Uso: `uv run python modulos/06-produccion/desplegar.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
RESULTADOS = AQUI / "resultados"
IMAGEN = "asistente-curso:leccion"
URL = "http://127.0.0.1:8101"
PUERTOS = ["-p", "127.0.0.1:8101:8100"]
# Dentro del contenedor, 127.0.0.1 es el propio contenedor: Ollama y el reranker están en
# el anfitrión. CURSO_URL_<PROVEEDOR> cambia la URL sin tocar config/models.toml.
ENTORNO = [
    "-e",
    "CURSO_URL_OLLAMA=http://host.docker.internal:11434",
    "-e",
    "CURSO_URL_LLAMACPP_RERANK=http://host.docker.internal:8082/v1",
]
COMANDO = "uvicorn servicio:app --app-dir modulos/06-produccion --host 0.0.0.0 --port 8100"
PREGUNTA = "¿Cada cuánto caduca el token de la API del banco?"
# Busca secretos en los ficheros de la aplicación, dentro de la imagen (sin el .venv).
ESCANEO = """
import pathlib, sys
sys.path.insert(0, "modulos/06-produccion")
import privacidad
fs = [p for p in pathlib.Path(".").rglob("*") if p.is_file() and ".venv" not in p.parts]
hallados = sum(len(privacidad.buscar_secretos(p.read_text(errors="ignore"))) for p in fs)
print(hallados, len(fs))
"""
sys.path.insert(0, str(AQUI.parent / "04-evals"))


def docker(*args: str, check: bool = True) -> str:
    r = subprocess.run(
        ["docker", *args], capture_output=True, text=True, encoding="utf-8", cwd=RAIZ
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"docker {args[0]} falló:\n{r.stderr.strip()[-1500:]}")
    return r.stdout.strip()


def construir(*extra: str) -> float:
    inicio = time.perf_counter()
    docker("build", "-q", *extra, "-f", "modulos/06-produccion/Dockerfile", "-t", IMAGEN, ".")
    return time.perf_counter() - inicio


def parte_construir() -> dict:
    desde_cero = construir("--no-cache")
    servicio = AQUI / "servicio.py"
    original = servicio.read_text(encoding="utf-8")
    try:
        servicio.write_text(original + "\n# cambio de prueba\n", encoding="utf-8")
        tras_cambio = construir()
    finally:
        servicio.write_text(original, encoding="utf-8")
    construir()  # deja la imagen como estaba
    return {"desde_cero_s": desde_cero, "tras_cambiar_el_servicio_s": tras_cambio}


def a_bytes(talla: str) -> float:
    """'311MB' o '24.6kB', como los escribe docker history, en bytes."""
    unidades = {"GB": 1e9, "MB": 1e6, "kB": 1e3, "B": 1}
    for unidad, factor in unidades.items():
        if talla.endswith(unidad):
            return float(talla[: -len(unidad)]) * factor
    return 0.0


def parte_imagen() -> dict:
    # Con el almacén de imágenes de containerd, Size es lo comprimido (lo que se descarga);
    # `docker images` da lo que ocupa descomprimida en disco.
    comprimida = int(docker("image", "inspect", IMAGEN, "--format", "{{.Size}}"))
    en_disco = docker("images", IMAGEN, "--format", "{{.Size}}")
    capas = []
    for linea in docker("history", IMAGEN, "--format", "{{.Size}}\t{{.CreatedBy}}").splitlines():
        talla, orden = linea.split("\t", 1)
        capas.append({"tamano": talla, "orden": orden[:70]})
    capas.sort(key=lambda c: a_bytes(c["tamano"]), reverse=True)
    ficheros = docker("run", "--rm", "--entrypoint", "ls", IMAGEN, "-a", "/app").split()
    variables = json.loads(docker("image", "inspect", IMAGEN, "--format", "{{json .Config.Env}}"))
    hallados, revisados = docker(
        "run", "--rm", "--entrypoint", "python", IMAGEN, "-c", ESCANEO
    ).split()
    return {
        "comprimida_mb": comprimida / 1e6,
        "en_disco": en_disco,
        "capas": capas[:5],
        "env_en_app": ".env" in ficheros,
        "variables": variables,
        "secretos_en_el_codigo": int(hallados),
        "ficheros_revisados": int(revisados),
    }


def esperar_salud(timeout: float = 180) -> float:
    inicio = time.perf_counter()
    while time.perf_counter() - inicio < timeout:
        try:
            httpx.get(f"{URL}/salud", timeout=2).raise_for_status()
            return time.perf_counter() - inicio
        except httpx.HTTPError:
            time.sleep(0.5)
    raise RuntimeError("El contenedor no respondió")


def parte_arrancar() -> dict:
    import evaluar

    docker("rm", "-f", "asistente-leccion", check=False)
    docker("run", "-d", "--name", "asistente-leccion", *PUERTOS, *ENTORNO, IMAGEN)
    hasta_salud = esperar_salud()
    salud = httpx.get(f"{URL}/salud").json()
    t0 = time.perf_counter()
    primera = httpx.post(f"{URL}/preguntas", json={"pregunta": PREGUNTA}, timeout=300).json()
    primera_s = time.perf_counter() - t0
    estado = "starting"
    for _ in range(40):  # el healthcheck pasa a "healthy" en su siguiente comprobación
        estado = docker("inspect", "asistente-leccion", "--format", "{{.State.Health.Status}}")
        if estado != "starting":
            break
        time.sleep(2)
    memoria = docker("stats", "--no-stream", "--format", "{{.MemUsage}}", "asistente-leccion")
    return {
        "hasta_salud_s": hasta_salud,
        "version_servida": salud["version"],
        "version_medida": evaluar.huella(),
        "primera_s": primera_s,
        "primera": primera["texto"],
        "salud_docker": estado,
        "memoria": memoria,
    }


def parar(nombre: str) -> dict:
    inicio = time.perf_counter()
    docker("stop", nombre)
    segundos = time.perf_counter() - inicio
    codigo = int(docker("inspect", nombre, "--format", "{{.State.ExitCode}}"))
    # uvicorn escribe sus logs en stderr; al cerrar con orden, termina con esta línea.
    logs = subprocess.run(
        ["docker", "logs", nombre], capture_output=True, text=True, encoding="utf-8"
    ).stderr
    docker("rm", nombre)
    return {"s": segundos, "codigo": codigo, "cierre_ordenado": "Finished server process" in logs}


def parte_parar() -> dict:
    exec_ = parar("asistente-leccion")
    # El mismo servicio, lanzado a través de un shell (como hace la forma `CMD comando`).
    docker(
        "run",
        "-d",
        "--name",
        "asistente-shell",
        *PUERTOS,
        *ENTORNO,
        "--entrypoint",
        "sh",
        IMAGEN,
        "-c",
        COMANDO,
    )
    esperar_salud()
    return {"exec": exec_, "shell": parar("asistente-shell")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no usa Docker")
    args = parser.parse_args()
    ruta = RESULTADOS / "despliegue.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = {"construir": parte_construir(), "imagen": parte_imagen()}
        r["arrancar"] = parte_arrancar()
        r["parar"] = parte_parar()
        RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    c = r["construir"]
    print("1. Construir la imagen")
    print(f"   desde cero: {c['desde_cero_s']:.0f} s")
    print(f"   tras cambiar una línea de servicio.py: {c['tras_cambiar_el_servicio_s']:.1f} s")

    i = r["imagen"]
    print(f"\n2. La imagen: {i['comprimida_mb']:.0f} MB comprimida, {i['en_disco']} en disco")
    print("   las capas más pesadas:")
    for capa in i["capas"]:
        print(f"   {capa['tamano']:>8}  {capa['orden']}")
    print(f"   .env dentro de /app: {'SÍ' if i['env_en_app'] else 'no'}")
    print(f"   variables de la imagen: {', '.join(v.split('=')[0] for v in i['variables'])}")
    secretos, revisados = i["secretos_en_el_codigo"], i["ficheros_revisados"]
    print(f"   secretos en el código: {secretos} en {revisados} ficheros")

    a = r["arrancar"]
    print("\n3. Arrancar")
    print(f"   de `docker run` a responder /salud: {a['hasta_salud_s']:.1f} s")
    print(f"   versión del sistema que sirve: {a['version_servida']}")
    print(f"   versión que midió el módulo 4: {a['version_medida']}")
    print(f"   primera pregunta: {a['primera_s']:.1f} s → {a['primera']}")
    print(f"   healthcheck de Docker: {a['salud_docker']} · memoria: {a['memoria']}")

    p = r["parar"]
    print("\n4. Parar con `docker stop`")
    for nombre, x in (
        ("uvicorn como proceso principal", p["exec"]),
        ("a través de `sh -c`", p["shell"]),
    ):
        cierre = "uvicorn cerró con orden" if x["cierre_ordenado"] else "uvicorn no llegó a cerrar"
        print(f"   {nombre:32} {x['s']:4.1f} s · código {x['codigo']:>3} · {cierre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

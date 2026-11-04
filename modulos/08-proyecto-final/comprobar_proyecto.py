"""Módulo 8: comprueba los requisitos mínimos de un proyecto a partir de su `proyecto.toml`.

El manifiesto dice dónde está cada pieza del proyecto (especificación, dataset de la eval,
resultados, código, tests, observabilidad, coste, README). El comprobador no se fía de
que existan: mira lo que contienen y da, para cada requisito, OK, AVISO o FALTA, con la
evidencia.

No llama a ningún modelo. Con --tests, además, ejecuta los tests del proyecto.
Uso: `uv run python modulos/08-proyecto-final/comprobar_proyecto.py <proyecto.toml> [--tests]`
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "06-produccion"))

# Mínimos del curso. Con 30 casos, el intervalo del 95 % de un 80 % de aciertos va de
# un 63 % a un 90 %: por debajo, la eval no distingue casi nada (lección 4.03).
MIN_CASOS = 30
CAMPOS_ESPECIFICACION = ["problema", "usuarios", "metrica", "umbral", "linea_base", "fuera_de_alcance"]  # fmt: skip  # noqa: E501
SECCIONES_README = ["problema", "cómo ejecutarlo", "resultados", "decisiones", "coste", "límites"]
SENALES_TRAZAS = re.compile(r"emitir_span|opentelemetry|tracing|span|\.trazas\b", re.I)
SENALES_METRICAS = re.compile(r"prometheus|latencia|p95|counter|histogram", re.I)
# Las claves de un resultado grabado que cuentan como medida de cada parte del coste.
SENALES_COSTE = {
    "tokens": re.compile(r'"tokens\w*"'),
    "latencia": re.compile(r'"(?:latencia\w*|p50\w*|p95\w*)"'),
    "dinero": re.compile(r'"coste\w*"'),
}


@dataclass
class Comprobacion:
    requisito: str
    estado: str  # OK, AVISO o FALTA
    evidencia: str


def leer_jsonl(ruta: Path) -> list[dict]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea]


def ultimo_commit(raiz: Path, rutas: list[str]) -> int | None:
    """Fecha (epoch) del último commit que tocó alguna de las rutas; None sin git."""
    r = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", *rutas],
        cwd=raiz,
        capture_output=True,
        text=True,
    )
    return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def comprobar_especificacion(m: dict) -> Comprobacion:
    espec = m.get("especificacion", {})
    faltan = [c for c in CAMPOS_ESPECIFICACION if not str(espec.get(c, "")).strip()]
    if faltan:
        return Comprobacion("especificación", "FALTA", f"sin {', '.join(faltan)}")
    return Comprobacion(
        "especificación", "OK", f"métrica «{espec['metrica']}», umbral {espec['umbral']}"
    )


def comprobar_dataset(raiz: Path, m: dict) -> Comprobacion:
    from curso_core.evals import intervalo_wilson

    ruta = raiz / m.get("evals", {}).get("dataset", "")
    if not ruta.is_file():
        return Comprobacion(
            "dataset de la eval", "FALTA", f"no existe {ruta.relative_to(raiz).as_posix()}"
        )
    n = len(leer_jsonl(ruta))
    umbral = float(m.get("especificacion", {}).get("umbral", 0.8))
    bajo, alto = intervalo_wilson(round(umbral * n), n)
    evidencia = f"{n} casos; con un {umbral:.0%} de aciertos, IC 95 % {bajo:.0%}-{alto:.0%}"
    return Comprobacion("dataset de la eval", "OK" if n >= MIN_CASOS else "FALTA", evidencia)


def comprobar_resultados(raiz: Path, m: dict) -> Comprobacion:
    from curso_core.evals import intervalo_wilson

    evals = m.get("evals", {})
    ruta = raiz / evals.get("resultados", "")
    if not ruta.is_file():
        return Comprobacion("resultados de la eval", "FALTA", "no hay resultados grabados")
    filas = [f for f in leer_jsonl(ruta) if "ok" in f]
    aciertos = sum(bool(f["ok"]) for f in filas)
    bajo, alto = intervalo_wilson(aciertos, len(filas))
    umbral = float(m.get("especificacion", {}).get("umbral", 0))
    evidencia = f"{aciertos} de {len(filas)} ({bajo:.0%}-{alto:.0%})"
    estado = "OK" if bajo >= umbral else "AVISO"
    if estado == "AVISO":
        evidencia += f": el umbral es {umbral:.0%} y el intervalo baja de él"
    sistema = m.get("codigo", {}).get("sistema", [])
    cuando_resultados = ultimo_commit(raiz, [evals["resultados"]])
    cuando_sistema = ultimo_commit(raiz, sistema)
    if cuando_resultados and cuando_sistema and cuando_sistema > cuando_resultados:
        return Comprobacion(
            "resultados de la eval",
            "FALTA",
            evidencia + "; el sistema cambió después de la última eval",
        )
    return Comprobacion("resultados de la eval", estado, evidencia)


def comprobar_tests(raiz: Path, m: dict, ejecutar: bool) -> Comprobacion:
    carpetas = m.get("codigo", {}).get("tests", [])
    ficheros = [f for c in carpetas for f in (raiz / c).rglob("test_*.py")]
    if not ficheros:
        return Comprobacion("tests", "FALTA", "no hay ficheros test_*.py")
    if not ejecutar:
        # Sin el número de ficheros: cambia con cada test nuevo y no dice si funcionan.
        return Comprobacion("tests", "OK", "hay tests (sin ejecutar: usa --tests)")
    r = subprocess.run(
        ["uv", "run", "pytest", "-q", *carpetas], cwd=raiz, capture_output=True, text=True
    )
    resumen = (r.stdout.strip().splitlines() or ["sin salida"])[-1]
    return Comprobacion("tests", "OK" if r.returncode == 0 else "FALTA", resumen)


def comprobar_observabilidad(raiz: Path, m: dict) -> list[Comprobacion]:
    obs = m.get("observabilidad", {})
    salida = []
    for clave, senales, nombre in (
        ("trazas", SENALES_TRAZAS, "trazas"),
        ("metricas", SENALES_METRICAS, "métricas"),
    ):
        rutas = [raiz / r for r in obs.get(clave, [])]
        con_senal = [r for r in rutas if r.is_file() and senales.search(r.read_text("utf-8"))]
        if con_senal:
            salida.append(
                Comprobacion(
                    nombre, "OK", ", ".join(r.relative_to(raiz).as_posix() for r in con_senal)
                )
            )
        else:
            salida.append(Comprobacion(nombre, "FALTA", "ningún fichero con instrumentación"))
    return salida


def comprobar_coste(raiz: Path, m: dict) -> Comprobacion:
    """El coste tiene que estar medido: tokens, latencia y dinero, en algún resultado grabado."""
    rutas = [raiz / r for r in m.get("coste", {}).get("medidas", [])]
    texto = "\n".join(r.read_text(encoding="utf-8") for r in rutas if r.is_file())
    faltan = [nombre for nombre, senal in SENALES_COSTE.items() if not senal.search(texto)]
    if faltan:
        return Comprobacion("coste medido", "FALTA", f"no hay medidas de {', '.join(faltan)}")
    return Comprobacion("coste medido", "OK", "tokens, latencia y dinero en resultados grabados")


def comprobar_secretos(raiz: Path, m: dict) -> Comprobacion:
    import privacidad

    rutas = m.get("codigo", {}).get("raices", ["."])
    r = subprocess.run(["git", "ls-files", *rutas], cwd=raiz, capture_output=True, text=True)
    ficheros = [raiz / f for f in r.stdout.splitlines()]
    if not ficheros:
        return Comprobacion("secretos", "AVISO", "ningún fichero en git: haz commit y repite")
    if any(f.name == ".env" for f in ficheros):
        return Comprobacion("secretos", "FALTA", ".env está en el repositorio")
    # Valores que se sabe que son falsos (datos de prueba), declarados uno a uno en el
    # manifiesto con su motivo. Nunca se desactiva la comprobación entera.
    permitidos = m.get("secretos", {}).get("de_prueba", [])
    hallados, de_prueba = [], 0
    for f in ficheros:
        if f.suffix in {".py", ".toml", ".md", ".yaml", ".yml", ".json", ".txt"} and f.is_file():
            for _, linea in privacidad.buscar_secretos(f.read_text("utf-8", errors="ignore")):
                if any(valor in linea for valor in permitidos):
                    de_prueba += 1
                else:
                    hallados.append((f, linea))
    if hallados:
        f, linea = hallados[0]
        return Comprobacion(
            "secretos",
            "FALTA",
            f"{len(hallados)}, p. ej. {f.relative_to(raiz).as_posix()}: {linea[:60]}",
        )
    extra = f" ({de_prueba} con valores de prueba declarados)" if de_prueba else ""
    return Comprobacion("secretos", "OK", f"ninguno en los ficheros versionados{extra}")


def comprobar_modelos(raiz: Path, m: dict) -> Comprobacion:
    """Los nombres de modelo, en la configuración y no en el código."""
    relativa = m.get("codigo", {}).get("config_modelos")
    if relativa:
        config = raiz / relativa
    else:  # la más cercana subiendo desde el proyecto, como la busca curso_core
        config = next(
            (c / "config" / "models.toml" for c in [raiz, *raiz.parents]
             if (c / "config" / "models.toml").is_file()),
            raiz / "config" / "models.toml",
        )  # fmt: skip
    if not config.is_file():
        return Comprobacion("modelos en configuración", "FALTA", "sin fichero de configuración")
    nombres = {
        rol["model"]
        for rol in tomllib.loads(config.read_text("utf-8")).get("roles", {}).values()
        if len(rol.get("model", "")) > 5
    }
    sistema = [raiz / r for r in m.get("codigo", {}).get("sistema", [])]
    en_codigo = [
        (f.relative_to(raiz).as_posix(), n)
        for f in sistema
        if f.is_file()
        for n in nombres
        if f'"{n}"' in f.read_text("utf-8")
    ]
    if en_codigo:
        f, n = en_codigo[0]
        return Comprobacion("modelos en configuración", "FALTA", f"{n} escrito en {f}")
    return Comprobacion(
        "modelos en configuración", "OK", f"{len(nombres)} modelos, ninguno en el código"
    )


def comprobar_readme(raiz: Path, m: dict) -> Comprobacion:
    ruta = raiz / m.get("proyecto", {}).get("readme", "README.md")
    if not ruta.is_file():
        return Comprobacion("README", "FALTA", f"no existe {ruta.relative_to(raiz).as_posix()}")
    titulos = [t.strip().lower() for t in re.findall(r"^#+\s*(.+)$", ruta.read_text("utf-8"), re.M)]
    faltan = [s for s in SECCIONES_README if not any(s in t for t in titulos)]
    if faltan:
        return Comprobacion("README", "FALTA", f"sin sección de {', '.join(faltan)}")
    return Comprobacion("README", "OK", f"las {len(SECCIONES_README)} secciones")


def comprobar(manifiesto: Path, ejecutar_tests: bool = False) -> tuple[dict, list[Comprobacion]]:
    m = tomllib.loads(manifiesto.read_text(encoding="utf-8"))
    raiz = (manifiesto.parent / m.get("proyecto", {}).get("raiz", ".")).resolve()
    return m, [
        comprobar_especificacion(m),
        comprobar_dataset(raiz, m),
        comprobar_resultados(raiz, m),
        comprobar_tests(raiz, m, ejecutar_tests),
        *comprobar_observabilidad(raiz, m),
        comprobar_coste(raiz, m),
        comprobar_secretos(raiz, m),
        comprobar_modelos(raiz, m),
        comprobar_readme(raiz, m),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifiesto", type=Path, help="ruta a proyecto.toml")
    parser.add_argument("--tests", action="store_true", help="ejecuta también los tests")
    args = parser.parse_args()
    m, resultado = comprobar(args.manifiesto, args.tests)
    print(f"Proyecto: {m.get('proyecto', {}).get('nombre') or '(sin nombre)'}")
    for c in resultado:
        print(f"   {c.estado:5} {c.requisito:26} {c.evidencia}")
    faltan = sum(c.estado == "FALTA" for c in resultado)
    avisos = sum(c.estado == "AVISO" for c in resultado)
    print(f"   {len(resultado) - faltan - avisos} OK, {avisos} avisos, {faltan} por hacer")
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(main())

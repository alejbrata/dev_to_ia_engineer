"""Lección 6.08: un cambio de modelo llevado a producción con cuidado.

El cambio es el de la lección 6.07, pero hecho a propósito: pasar el modelo principal
del de 7B al de 1,5B, cuatro veces más rápido. En cuatro partes:
1. En sombra: el candidato responde las 58 preguntas del módulo 4 sin servir nada, y se
   compara caso a caso con el vigente. Es la puerta antes de mandarle tráfico.
2. Canario: un 25 % del tráfico (elegido por la pregunta, siempre el mismo) va al
   candidato. Se comparan las señales que hay en producción (abstenciones, respuestas sin
   citas, latencia) con la calidad real, que aquí se conoce porque el tráfico sale del
   dataset.
3. Vuelta atrás: el canario se apaga y el mismo tráfico vuelve al vigente, con una caché
   compartida entre versiones (como un Redis). Primero con la clave de la caché de la
   lección 6.01, después con la que incluye el modelo.
4. Postmortem: el informe sin culpas, generado con los datos de las partes anteriores.

Necesita Ollama con los modelos del módulo 4 y el reranker en llama-server. Unos 20
minutos; con --grabadas, un segundo.
Uso: `uv run python modulos/06-produccion/cambios_seguros.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from statistics import median

from curso_core import config as cfg

AQUI = Path(__file__).resolve().parent
RESULTADOS = cfg.carpeta_resultados(AQUI / "resultados")
sys.path.insert(0, str(AQUI.parent / "04-evals"))

VIGENTE = ("chat_grande", "chat")  # el sistema vigente: 7B y, de respaldo, 1,5B
CANDIDATA = ("chat",)  # el cambio propuesto: el de 1,5B como principal
PORCENTAJE = 25
PETICIONES = 60
# Regla de vuelta atrás: con al menos MINIMO respuestas del canario, si una señal empeora
# más de lo tolerado frente al vigente, se vuelve atrás sin esperar a nadie.
MINIMO = 10
TOLERANCIA = {"sin_citas": 0.10, "abstenciones": 0.15, "p95_ms": 1.5}


def en_canario(pregunta: str, porcentaje: int) -> bool:
    """Siempre la misma decisión para la misma pregunta (o el mismo usuario): si el reparto
    fuera al azar en cada petición, la misma pregunta saldría de dos versiones distintas."""
    from asistente import normalizar

    cubo = int(hashlib.sha256(normalizar(pregunta).encode()).hexdigest(), 16) % 100
    return cubo < porcentaje


def senales(filas: list[dict]) -> dict:
    """Lo que se ve en producción, sin saber cuál es la respuesta correcta."""
    n = len(filas)
    if not n:
        return {"n": 0}
    ms = sorted(f["ms"] for f in filas)
    return {
        "n": n,
        "abstenciones": sum(f["abstencion"] for f in filas) / n,
        "sin_citas": sum(f["sin_citas"] for f in filas) / n,
        "p50_ms": median(ms),
        "p95_ms": ms[min(n - 1, int(0.95 * n))],
        "aciertos": sum(f["ok"] for f in filas) / n,  # esto no se ve en producción
    }


def volver_atras(vigente: dict, canario: dict) -> list[str]:
    """Los motivos para volver atrás, o ninguno. Solo mira lo que se ve en producción."""
    if canario.get("n", 0) < MINIMO:
        return []
    motivos = []
    for senal in ("sin_citas", "abstenciones"):
        if canario[senal] - vigente[senal] > TOLERANCIA[senal]:
            motivos.append(f"{senal}: {canario[senal]:.0%} frente a {vigente[senal]:.0%}")
    if canario["p95_ms"] > TOLERANCIA["p95_ms"] * vigente["p95_ms"]:
        motivos.append(f"p95: {canario['p95_ms']:.0f} ms frente a {vigente['p95_ms']:.0f} ms")
    return motivos


def fila(caso, version: str, r) -> dict:
    import dataset

    abstencion = dataset.se_niega(r.texto)
    return {
        "caso": caso.id,
        "version": version,
        "ok": dataset.puntuar(caso, r.texto),
        "abstencion": abstencion,
        "sin_citas": not abstencion and not r.citas,
        "ms": r.ms,
        "cache": r.cache,
        "modelo": r.modelo,
    }


def medir() -> dict:
    import arquitectura
    import dataset
    import evaluar
    from asistente import Asistente, Cache
    from curso_core.evals import Informe

    casos = dataset.cargar()
    por_pregunta = {c.pregunta: c for c in casos}

    # 1. En sombra: el candidato responde todo; nadie recibe sus respuestas.
    candidata = Asistente(CANDIDATA, cache=False)
    sombra = [fila(c, "candidata", candidata.responder(c.pregunta)) for c in casos]
    vigente_grabado = Informe.cargar(evaluar.VIGENTE).por_caso()

    # 2. Canario, con la caché compartida de la lección 6.01 (clave: la huella).
    trafico = arquitectura.trafico([c.pregunta for c in casos], PETICIONES)
    compartida: dict = {}
    vigente, canario = Asistente(VIGENTE), Asistente(CANDIDATA)
    for a in (vigente, canario):
        a.cache = Cache(a.version, datos=compartida)  # la clave de antes: solo la huella
    servidas = []
    for pregunta in trafico:
        version = "candidata" if en_canario(pregunta, PORCENTAJE) else "vigente"
        a = canario if version == "candidata" else vigente
        servidas.append(fila(por_pregunta[pregunta], version, a.responder(pregunta)))

    # 3. Vuelta atrás: todo al vigente. Primero con la misma caché compartida...
    tras_volver = [
        fila(por_pregunta[p], "vigente", vigente.responder(p)) for p in dict.fromkeys(trafico)
    ]
    # ... y después repitiendo el canario con la clave que incluye el modelo.
    compartida_bien: dict = {}
    for a in (vigente, canario):
        a.cache = Cache(a.version_cache, datos=compartida_bien)
    for pregunta in trafico:
        if en_canario(pregunta, PORCENTAJE):
            canario.responder(pregunta)
        else:
            vigente.responder(pregunta)
    tras_volver_bien = [
        fila(por_pregunta[p], "vigente", vigente.responder(p)) for p in dict.fromkeys(trafico)
    ]
    return {
        "modelos": {
            "vigente": vigente.modelos[VIGENTE[0]],
            "candidata": canario.modelos[CANDIDATA[0]],
        },
        "sombra": sombra,
        "vigente_grabado": {k: v.ok for k, v in vigente_grabado.items()},
        "canario": servidas,
        "tras_volver": tras_volver,
        "tras_volver_bien": tras_volver_bien,
    }


def postmortem(r: dict, motivos: list[str], comparacion: dict) -> str:
    """El informe sin culpas, con lo que se midió. Lo que no está en los datos va como
    pregunta abierta, no como hecho."""
    vig, cand = r["modelos"]["vigente"].split(" @")[0], r["modelos"]["candidata"].split(" @")[0]
    contaminadas = sum(f["cache"] and f["modelo"] != vig for f in r["tras_volver"])
    canario = (
        "pidieron volver atrás: " + "; ".join(motivos) if motivos else "no pidieron volver atrás"
    )
    gana, pierde, p = comparacion["gana"], comparacion["pierde"], comparacion["p"]
    return f"""# Postmortem: el modelo de 1,5B como principal

## Resumen
Se propuso pasar el modelo principal del asistente de {vig} a {cand}, más rápido.
En sombra perdía {pierde} casos de la eval y ganaba {gana} (p = {p:.3f}). En canario, las
señales de producción {canario}.

## Impacto
Durante el canario, el {PORCENTAJE} % de las preguntas lo respondió el candidato. Tras volver
atrás, {contaminadas} respuestas del vigente salieron de la caché con el modelo del candidato.

## Causa
La clave de la caché era la huella del sistema, que no cambia si el modelo se elige por
configuración. Las dos versiones compartían las mismas claves.

## Qué funcionó
La evaluación en sombra detectó la pérdida de calidad antes de servir una sola respuesta.

## Acciones
- La clave de la caché incluye el modelo que responde (`Asistente.version_cache`).
- Ningún cambio de modelo pasa a canario sin la eval en sombra.
- Revisar qué señales de producción habrían detectado la pérdida de calidad.
"""


def main() -> int:
    from curso_core.evals import prueba_mcnemar

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama a los modelos")
    args = parser.parse_args()
    ruta = RESULTADOS / "cambios_seguros.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        from dotenv import load_dotenv

        load_dotenv()
        r = medir()
        RESULTADOS.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    vig, cand = r["modelos"]["vigente"].split(" @")[0], r["modelos"]["candidata"].split(" @")[0]
    grabado = r["vigente_grabado"]
    sombra = {f["caso"]: f for f in r["sombra"]}
    gana = [k for k, f in sombra.items() if f["ok"] and not grabado[k]]
    pierde = [k for k, f in sombra.items() if not f["ok"] and grabado[k]]
    p = prueba_mcnemar(len(gana), len(pierde))
    print(f"1. En sombra: {cand} responde las 58 preguntas, sin servir nada")
    print(f"   vigente ({vig}): {sum(grabado.values())} de 58 (grabado en el módulo 4)")
    print(f"   candidata ({cand}): {sum(f['ok'] for f in r['sombra'])} de 58")
    print(f"   la candidata gana {len(gana)} y pierde {len(pierde)}, p = {p:.3f}")
    s_sombra = senales(r["sombra"])
    print(
        f"   abstenciones {s_sombra['abstenciones']:.0%} · sin citas {s_sombra['sin_citas']:.0%}"
        f" · p50 {s_sombra['p50_ms'] / 1000:.1f} s"
    )

    print(f"\n2. Canario: el {PORCENTAJE} % del tráfico ({PETICIONES} peticiones) a la candidata")
    print(
        f"   {'':10} {'n':>3} {'abstenciones':>13} {'sin citas':>10} {'p50':>7} {'p95':>7}"
        f" {'aciertos*':>10}"
    )
    por_version = {}
    for version in ("vigente", "candidata"):
        filas = [f for f in r["canario"] if f["version"] == version]
        s = por_version[version] = senales(filas)
        print(
            f"   {version:10} {s['n']:>3} {s['abstenciones']:>13.0%} {s['sin_citas']:>10.0%}"
            f" {s['p50_ms'] / 1000:>6.1f}s {s['p95_ms'] / 1000:>6.1f}s {s['aciertos']:>10.0%}"
        )
    print(
        "   * los aciertos no se ven en producción: aquí se conocen porque el tráfico es el dataset"
    )
    motivos = volver_atras(por_version["vigente"], por_version["candidata"])
    print(f"   regla de vuelta atrás: {'; '.join(motivos) if motivos else 'no salta'}")

    print("\n3. Vuelta atrás: todo al vigente, con la caché compartida entre versiones")
    for etiqueta, clave in (("tras_volver", "la huella"), ("tras_volver_bien", "huella y modelo")):
        filas = r[etiqueta]
        de_cache = [f for f in filas if f["cache"]]
        ajenas = [f for f in de_cache if f["modelo"] != vig]
        print(
            f"   clave con {clave:16} {len(filas)} preguntas, {len(de_cache)} de la caché,"
            f" {len(ajenas)} respondidas por {cand}"
        )

    comparacion = {"gana": len(gana), "pierde": len(pierde), "p": p}
    texto = postmortem(r, motivos, comparacion)
    (RESULTADOS / "postmortem.md").write_text(texto, encoding="utf-8")
    print("\n4. Postmortem: resultados/postmortem.md")
    for linea in texto.splitlines()[2:6]:
        print(f"   {linea}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

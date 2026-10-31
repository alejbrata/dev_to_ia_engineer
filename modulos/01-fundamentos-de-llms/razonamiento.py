"""Modelos que razonan: qué ganas, qué pagas y cómo falla (lección 07).

1. Las mismas preguntas, con y sin razonar: aciertos, tokens de salida y tiempo. Unas
   necesitan varios pasos de cálculo; otras, no.
2. El límite de salida: razonando, el modelo puede gastarlo pensando y responder vacío.
3. Lo que hay dentro de esos tokens: el razonamiento que devuelve el servidor aparte.

Usa el rol `razonador` (un modelo que razona y permite desactivarlo).
Uso: `uv run python modulos/01-fundamentos-de-llms/razonamiento.py`
"""

from __future__ import annotations

import sys
import unicodedata

from curso_core import ClienteLLM, ErrorFormato, Opciones
from pydantic import BaseModel

ROL = "razonador"
# (pregunta, respuesta esperada, necesita varios pasos)
PREGUNTAS = [
    (
        "Un servicio recibe 120 peticiones por segundo y cada una tarda 250 ms. ¿Cuántas "
        "peticiones están en curso a la vez, de media? Responde solo con el número.",
        "30",
        True,
    ),
    (
        "Un pool tiene 200 conexiones y cada petición retiene una conexión durante 40 ms. "
        "¿Cuántas peticiones por segundo puede atender como máximo? Responde solo con el número.",
        "5000",
        True,
    ),
    (
        "Un despliegue empieza a las 22:45 y dura 95 minutos. ¿A qué hora termina? Responde "
        "solo con la hora en formato HH:MM.",
        "00:20",
        True,
    ),
    (
        "Tengo 3 réplicas y cada una aguanta 450 peticiones por segundo. Si cae una, "
        "¿cuántas peticiones por segundo aguanta el servicio? Responde solo con el número.",
        "900",
        True,
    ),
    ("¿Cuál es la capital de Francia? Responde con una sola palabra.", "paris", False),
    ("Traduce al inglés 'base de datos'. Responde solo con la traducción.", "database", False),
]


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().replace(".", "").replace(" ", "")


def acierta(respuesta: str, esperada: str) -> bool:
    return normalizar(esperada) in normalizar(respuesta)


class Numero(BaseModel):
    respuesta: int


def comparar(cliente: ClienteLLM) -> None:
    print("1. Las mismas preguntas, con y sin razonar")
    print(f"   {'':6} {'sin razonar':>24}   {'razonando':>24}")
    total = {False: [0, 0, 0.0], True: [0, 0, 0.0]}
    for pregunta, esperada, varios_pasos in PREGUNTAS:
        celdas = []
        for razonar in (False, True):
            # Límite amplio: aquí se mide cuánto razona, no se le corta.
            op = Opciones(temperatura=0, max_tokens=4000, razonar=razonar)
            r = cliente.chat(pregunta, rol=ROL, opciones=op)
            ok = acierta(r.texto, esperada)
            total[razonar][0] += ok
            total[razonar][1] += r.tokens_salida
            total[razonar][2] += r.latencia_s
            marca = "bien" if ok else "MAL "
            celdas.append(f"{marca} {r.tokens_salida:5} tok {r.latencia_s:5.1f} s")
        tipo = "pasos" if varios_pasos else "directa"
        print(f"   {tipo:6} {celdas[0]:>24}   {celdas[1]:>24}   {pregunta[:38]}...")
    n = len(PREGUNTAS)
    for razonar, (bien, tokens, segundos) in total.items():
        nombre = "razonando" if razonar else "sin razonar"
        print(f"   {nombre:12} {bien} de {n} bien · {tokens} tokens de salida · {segundos:.0f} s")


def limite(cliente: ClienteLLM) -> None:
    pregunta = PREGUNTAS[0][0]
    print("\n2. El mismo límite de salida (150 tokens), sin razonar y razonando")
    for razonar in (False, True):
        op = Opciones(temperatura=0, max_tokens=150, razonar=razonar)
        r = cliente.chat(pregunta, rol=ROL, opciones=op)
        nombre = "razonando" if razonar else "sin razonar"
        print(
            f"   {nombre:12} texto {r.texto.strip()!r:12} · {r.tokens_salida} tokens · "
            f"motivo_fin {r.motivo_fin}"
        )
    print("   Con salida estructurada (JSON), razonando y el mismo límite:")
    try:
        op = Opciones(temperatura=0, max_tokens=150, razonar=True)
        numero, r = cliente.extraer(pregunta, Numero, rol=ROL, opciones=op)
        print(f"   {numero}")
    except ErrorFormato as e:
        print(f"   ErrorFormato: {str(e).splitlines()[0][:90]}")
        print(f"   texto recibido {e.texto!r} · motivo_fin {e.respuesta.motivo_fin}")


def por_dentro(cliente: ClienteLLM) -> None:
    pregunta = PREGUNTAS[2][0]
    print("\n3. Lo que razona (la pregunta del despliegue)")
    r = cliente.chat(
        pregunta, rol=ROL, opciones=Opciones(temperatura=0, max_tokens=4000, razonar=True)
    )
    razonamiento = (r.razonamiento or "").strip()
    print(f"   razonamiento: {len(razonamiento)} caracteres · respuesta: {r.texto.strip()!r}")
    for linea in razonamiento.splitlines()[:8]:
        print(f"   | {linea[:96]}")
    print("   | [...]")


def main() -> int:
    cliente = ClienteLLM()
    cliente.descargar_modelo(ROL)
    comparar(cliente)
    limite(cliente)
    por_dentro(cliente)
    return 0


if __name__ == "__main__":
    sys.exit(main())

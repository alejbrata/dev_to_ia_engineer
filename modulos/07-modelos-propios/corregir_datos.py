"""Lección 7.06 (2): corregir los ejemplos en los que el maestro se abstuvo.

En 29 de los ejemplos que el generador marcó como "con respuesta", el maestro contestó
"No aparece en la documentación". Revisados uno a uno con el fragmento del que salió la
pregunta y el contexto que vio el maestro:

- En 9, la respuesta estaba en el contexto: el maestro se equivocó. Se corrigen con la
  respuesta y la cita, escritas a mano a partir del fragmento.
- En 15, el fragmento no da el dato que pide la pregunta (la etiqueta del generador era
  la equivocada): abstenerse era lo correcto, y se dejan.
- En 5, la pregunta es ambigua o la respuesta solo está a medias: se quitan.

Cada decisión está abajo con su motivo. Escribe `resultados/ajuste/datos-corregidos.jsonl`,
que usa `ajustar.py --datos corregidos`.
Uso: `uv run python modulos/07-modelos-propios/corregir_datos.py`
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados" / "ajuste"
DATOS = RESULTADOS / "datos.jsonl"
CORREGIDOS = RESULTADOS / "datos-corregidos.jsonl"
sys.path.insert(0, str(AQUI.parent / "04-evals"))

# Pregunta: (respuesta, citas) para corregir, o el motivo de dejarla o quitarla.
CORREGIR = {
    "¿Cuál es el método de indexación utilizado para el catálogo en OpenSearch?": (
        "Cada cambio en el catálogo genera un evento que el indexador recoge y aplica al "
        "índice en menos de un minuto.",
        [2],
    ),
    "¿Qué sucede si el índice no puede escribir y hay nuevos productos en el catálogo?": (
        "Los productos nuevos no aparecen en la búsqueda, pero los antiguos siguen funcionando.",
        [1],
    ),
    "¿Qué tipo de peticiones recibe la API de pagos?": (
        "Las peticiones de cobro que llegan desde el servicio de pedidos.",
        [1],
    ),
    "¿Qué sucede cuando una incidencia media no genera consultas del cliente?": (
        "No hace falta avisar a atención al cliente: en las incidencias medias solo se avisa "
        "si generan consultas.",
        [1],
    ),
    "¿Qué función tiene un interruptor de funcionalidad en la implementación de nuevas "
    "características?": (
        "Es una configuración que activa o desactiva una funcionalidad sin desplegar.",
        [1],
    ),
    "¿Cuáles son los umbrales de alerta para la tasa de errores en los servicios?": (
        "La alerta de errores documentada es PagosErroresAltos: más del 2 % de errores en "
        "pagos durante 5 minutos.",
        [3],
    ),
    "¿Qué indica el log exactamente cuando se detecta un deadlock en el servicio de usuarios?": (
        "En los logs del servicio de usuarios aparece «deadlock detected».",
        [1],
    ),
    "¿Qué tipo de secretos se incluyen en el gestor de secretos?": (
        "Todos los secretos: contraseñas, tokens y claves de API.",
        [1],
    ),
    "¿Qué proveedores tienen un plazo de caducidad fijado por ellos mismos y no por el sistema "
    "interno?": (
        "Los proveedores externos como los bancos, Google y Apple; esos secretos siguen el plazo "
        "del proveedor.",
        [1],
    ),
}
QUITAR = {
    "¿Cuáles son las características de los entornos de desarrollo y pruebas?": (
        "el fragmento solo dice que no tienen alertas de guardia"
    ),
    "¿Qué tipo de información debe recogerse y transmitirse al equipo técnico cuando se "
    "registra una incidencia?": "la pregunta no encaja con lo que dice el fragmento",
    "¿Cuántos días por semana tiene una persona de guardia en el equipo?": (
        "la pregunta mezcla días y semanas; el fragmento dice una persona por semana"
    ),
    "¿Qué indica que es necesario usar este runbook?": "«este runbook» sin decir cuál",
    "¿Qué sucede si la cola de emails se llena permanentemente y no se restablece la conexión "
    "con el servidor de correo?": "el fragmento solo lo insinúa («si la cola no se llena»)",
}
# Las 15 restantes piden un dato que el fragmento no da: abstenerse era lo correcto.


def corregir() -> dict:
    import dataset

    ejemplos = [json.loads(linea) for linea in DATOS.read_text(encoding="utf-8").splitlines()]
    salida, cuenta = [], Counter()
    for e in ejemplos:
        objetivo = json.loads(e["objetivo"])
        abstencion = e["tipo"] == "con_respuesta" and dataset.se_niega(objetivo["respuesta"])
        if not abstencion:
            salida.append(e)
            continue
        if e["pregunta"] in CORREGIR:
            respuesta, citas = CORREGIR[e["pregunta"]]
            nuevo = {"respuesta": respuesta, "citas": citas}
            salida.append(e | {"objetivo": json.dumps(nuevo, ensure_ascii=False)})
            cuenta["corregidos"] += 1
        elif e["pregunta"] in QUITAR:
            cuenta["quitados"] += 1
        else:
            salida.append(e)
            cuenta["abstención correcta"] += 1
    sin_usar = (set(CORREGIR) | set(QUITAR)) - {e["pregunta"] for e in ejemplos}
    if sin_usar:
        raise ValueError(f"Preguntas de la lista que no están en los datos: {sin_usar}")
    with CORREGIDOS.open("w", encoding="utf-8") as f:
        for e in salida:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    particiones = Counter(e["particion"] for e in salida)
    return {"revisados": sum(cuenta.values()), **cuenta, "particiones": dict(particiones)}


def main() -> int:
    r = corregir()
    print(f"1. Ejemplos «con respuesta» en los que el maestro se abstuvo: {r['revisados']}")
    print(f"   la respuesta estaba en el contexto (corregidos):   {r['corregidos']}")
    print(f"   el fragmento no da el dato (abstención correcta):  {r['abstención correcta']}")
    print(f"   ambiguos (quitados):                               {r['quitados']}")
    ent, val = r["particiones"]["entrenamiento"], r["particiones"]["validacion"]
    print(f"\n2. Datos corregidos: {ent} de entrenamiento y {val} de validación")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tool calling básico: el modelo pide consultar el estado del servicio y tu código lo hace.

Para cada ticket:

1. Se manda el ticket con la herramienta `estado_servicio` disponible.
2. Si el modelo pide usarla, tu código valida los argumentos y la ejecuta.
3. Se le devuelve el resultado y el modelo da la clasificación final.

El estado de los servicios es una página de estado simulada: un diccionario. Lo que
importa aquí es el viaje de ida y vuelta, no de dónde salen los datos.

Compara el modelo del curso (rol `chat`) con uno mayor (rol `chat_grande`).

Uso: `uv run python modulos/02-prompting/herramientas.py [--detalle]`
"""

from __future__ import annotations

import sys

import tickets
from curso_core import ClienteLLM, Herramienta, Mensaje, Opciones, Respuesta, prompts
from medir_prompts import empezar_de_cero
from pydantic import BaseModel, ValidationError

ROLES = ["chat", "chat_grande"]
OPCIONES = Opciones(temperatura=0, max_tokens=200)

# Una página de estado simulada, coherente con los tickets de evaluación.
ESTADO = {
    "pagos": "caído: el 100 % de las peticiones devuelve error 500",
    "usuarios": "degradado: errores en parte de las peticiones",
    "catalogo": "degradado: faltan imágenes en las fichas de producto",
    "notificaciones": "degradado: los emails no salen",
    "busqueda": "caído: no hay instancias disponibles",
}


class ArgsEstado(BaseModel):
    servicio: tickets.Servicio


HERRAMIENTA = Herramienta.desde(
    "estado_servicio",
    "Devuelve el estado actual de un servicio de la plataforma (operativo, degradado o caído).",
    ArgsEstado,
)


class Resultado(BaseModel):
    llamo: bool = False
    nombre_valido: bool = False
    args_validos: bool = False
    servicio_correcto: bool = False
    final: tickets.Clasificacion | None = None
    texto_final: str = ""
    traza: str = ""


def ejecutar(llamada) -> tuple[str, bool]:
    """Valida los argumentos y ejecuta la herramienta. Devuelve el resultado y si eran válidos."""
    try:
        args = ArgsEstado.model_validate(llamada.argumentos)
    except ValidationError as e:
        # El error vuelve al modelo como resultado: así puede corregirse en el siguiente paso.
        return f"Error en los argumentos: {e.errors()[0]['msg']}", False
    return ESTADO[args.servicio], True


def clasificar(cliente: ClienteLLM, rol: str, prompt, caso: tickets.Ticket) -> Resultado:
    resultado = Resultado()
    renderizado = prompts.renderizar(prompt, ticket=caso.texto)
    mensajes = renderizado.mensajes
    opciones = OPCIONES.model_copy(update={"herramientas": [HERRAMIENTA]})
    primera: Respuesta = cliente.chat(renderizado, rol=rol, opciones=opciones)
    final = primera

    if primera.llamadas:
        resultado.llamo = True
        llamada = primera.llamadas[0]
        resultado.nombre_valido = llamada.nombre == HERRAMIENTA.nombre
        salida, validos = (
            ejecutar(llamada) if resultado.nombre_valido else ("Herramienta desconocida", False)
        )
        resultado.args_validos = validos
        resultado.servicio_correcto = llamada.argumentos.get("servicio") == caso.esperado.servicio
        resultado.traza = f"{llamada.nombre}({llamada.argumentos}) -> {salida!r}"
        mensajes = [
            *mensajes,
            primera.como_mensaje(),
            Mensaje(role="tool", content=salida, respuesta_a=llamada),
        ]
        final = cliente.chat(mensajes, rol=rol, opciones=OPCIONES)
    else:
        resultado.traza = "sin llamada"

    resultado.final = tickets.leer_lineas(final.texto)
    resultado.texto_final = final.texto.strip()
    return resultado


def main() -> int:
    casos = tickets.cargar("eval")
    cliente = ClienteLLM()
    prompt = prompts.cargar("tickets/con-herramienta")
    n = len(casos)
    print(f"{'modelo':14} {'llama':>6} {'args válidos':>12} {'servicio ok':>11} {'las 3':>6}")
    detalles = []
    for rol in ROLES:
        _, _, modelo = cliente.config.resolver(rol)
        empezar_de_cero(cliente, rol)
        resultados = [clasificar(cliente, rol, prompt, c) for c in casos]
        bien = sum(r.final == c.esperado for r, c in zip(resultados, casos, strict=True))
        print(
            f"{modelo:14} {sum(r.llamo for r in resultados):>3}/{n} "
            f"{sum(r.args_validos for r in resultados):>9}/{n} "
            f"{sum(r.servicio_correcto for r in resultados):>8}/{n} {bien:>3}/{n}"
        )
        for r, c in zip(resultados, casos, strict=True):
            final = (
                f"{r.final.categoria}/{r.final.severidad}/{r.final.servicio}"
                if r.final
                else f"NULO: {r.texto_final!r}"
            )
            detalles.append(f"  [{modelo}] {c.id:2} {r.traza} => {final}")
    if "--detalle" in sys.argv:
        print("\n" + "\n".join(detalles))
    return 0


if __name__ == "__main__":
    sys.exit(main())

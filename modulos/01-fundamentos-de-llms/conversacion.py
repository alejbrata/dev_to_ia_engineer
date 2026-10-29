"""Mensajes y roles: el modelo no recuerda nada entre llamadas.

1. Sin historial, la segunda pregunta no tiene respuesta.
2. Reenviando el historial, sí.
3. El mensaje de sistema cambia el comportamiento de toda la conversación.

Uso: `uv run python modulos/01-fundamentos-de-llms/conversacion.py`
"""

from __future__ import annotations

import sys

from curso_core import ClienteLLM, Mensaje, Opciones

DATO = "Estoy migrando un servicio que se llama Atlas de Java 8 a Java 21."
PREGUNTA = "¿Cómo se llama el servicio que estoy migrando? Responde solo con el nombre."
OPCIONES = Opciones(temperatura=0, max_tokens=60)


def usuario(texto: str) -> Mensaje:
    return Mensaje(role="user", content=texto)


def main() -> int:
    cliente = ClienteLLM()

    print("1. Dos llamadas independientes")
    primera = cliente.chat(DATO, opciones=OPCIONES)
    segunda = cliente.chat(PREGUNTA, opciones=OPCIONES)
    print(f"   > {PREGUNTA}\n   {segunda.texto.strip()!r} ({segunda.tokens_entrada} tokens)\n")

    print("2. La segunda llamada reenvía el historial")
    historial = [
        usuario(DATO),
        Mensaje(role="assistant", content=primera.texto),
        usuario(PREGUNTA),
    ]
    con_historial = cliente.chat(historial, opciones=OPCIONES)
    print(f"   > {PREGUNTA}")
    print(f"   {con_historial.texto.strip()!r} ({con_historial.tokens_entrada} tokens)\n")

    print("3. Mismo historial con un mensaje de sistema")
    sistema = Mensaje(
        role="system", content="Responde siempre en inglés y en mayúsculas, sin nada más."
    )
    con_sistema = cliente.chat([sistema, *historial], opciones=OPCIONES)
    print(f"   {con_sistema.texto.strip()!r} ({con_sistema.tokens_entrada} tokens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

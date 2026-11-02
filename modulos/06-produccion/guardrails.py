"""Guardrails del asistente: comprobaciones en código antes y después del modelo (6.05).

Entrada (la pregunta, antes de buscar y generar):
- inyección: frases típicas de quien intenta dar órdenes al modelo. Bloquea.
- datos personales: se redactan antes de enviar la pregunta al modelo. No bloquea.

Salida (la respuesta, antes de devolverla):
- sin fundamento: no es una abstención y no cita ningún fragmento válido. Bloquea.
- contacto externo: un correo o una URL. La documentación no tiene ninguno, así que no
  puede venir de ella. Bloquea.
- credenciales: pide enviar o compartir credenciales. Bloquea.
- comando destructivo: SQL o shell que borra datos. Bloquea.
- datos personales: se redactan. No bloquea.

Una respuesta bloqueada se sustituye por la abstención de siempre: el usuario no sabe qué
regla saltó, y quien opera el servicio lo ve en el motivo.
"""

from __future__ import annotations

import re

import privacidad
from pydantic import BaseModel

ABSTENCION = "No aparece en la documentación"

INYECCION = re.compile(
    r"(?i)\b(?:ignora|olvida|olvídate de|no sigas)\b.{0,40}\b(?:instrucciones|reglas|documentación|"
    r"indicaciones)\b|\ba partir de ahora\b|\bresponde (?:solo|únicamente) con\b|"
    r"\b(?:prompt|instrucciones) (?:del sistema|que te han dado|anteriores)\b|"
    r"\bignore (?:all |any |the )?(?:previous |prior )?instructions\b"
)
CONTACTO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|https?://\S+|\bwww\.\S+", re.IGNORECASE)
CREDENCIALES = re.compile(
    r"(?i)\b(?:envía|envíe|enviar|manda|mandar|comparte|compartir|facilita|facilitar|reenvía)\b"
    r".{0,80}\b(?:credenciales|contraseñas?|password|tokens?|claves?)\b"
)
DESTRUCTIVO = re.compile(r"(?i)\b(?:drop\s+table|truncate\s+table|delete\s+from|rm\s+-rf)\b")


class Veredicto(BaseModel):
    texto: str  # la pregunta o la respuesta, ya limpia
    bloqueado: bool = False
    motivos: list[str] = []


def revisar_entrada(pregunta: str) -> Veredicto:
    if INYECCION.search(pregunta):
        return Veredicto(texto=pregunta, bloqueado=True, motivos=["inyección en la pregunta"])
    limpia = privacidad.redactar(pregunta)
    motivos = ["datos personales redactados"] if limpia != pregunta else []
    return Veredicto(texto=limpia, motivos=motivos)


def revisar_salida(respuesta: str, citas: list[int] | None, n_fuentes: int) -> Veredicto:
    motivos = []
    abstiene = respuesta.strip().rstrip(".") == ABSTENCION
    validas = [c for c in citas or [] if 1 <= c <= n_fuentes]
    if not abstiene and not validas:
        motivos.append("sin fundamento: no cita ningún fragmento")
    if CONTACTO.search(respuesta):
        motivos.append("contacto externo")
    if CREDENCIALES.search(respuesta):
        motivos.append("pide enviar credenciales")
    if DESTRUCTIVO.search(respuesta):
        motivos.append("comando destructivo")
    if motivos:
        return Veredicto(texto=ABSTENCION, bloqueado=True, motivos=motivos)
    limpia = privacidad.redactar(respuesta)
    return Veredicto(
        texto=limpia, motivos=["datos personales redactados"] if limpia != respuesta else []
    )

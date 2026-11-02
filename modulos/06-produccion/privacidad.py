"""Datos personales y secretos en texto: detectarlos y redactarlos (lecciones 6.04 y 6.05).

Con expresiones regulares, sin modelos: rápido, predecible y fácil de auditar, pero solo
encuentra lo que tiene forma reconocible (un email, un DNI, un IBAN). Un nombre propio o
una dirección postal no tienen forma fija y se escapan; para eso hacen falta modelos de
reconocimiento de entidades, con sus propios errores.
"""

from __future__ import annotations

import re

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"

# El orden importa: lo más específico primero, para que un IBAN no acabe redactado como
# teléfono o como tarjeta.
PATRONES = {
    "IBAN": re.compile(r"\bES\d{2}(?:[ ]?\d{4}){5}\b"),
    "TARJETA": re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "DNI": re.compile(r"\b(\d{8})[- ]?([A-Z])\b"),
    "NIE": re.compile(r"\b([XYZ])[- ]?(\d{7})[- ]?([A-Z])\b"),
    "TELEFONO": re.compile(r"(?<![\d.])(?:\+34[ ]?)?[6789]\d{2}(?:[ .-]?\d{3}){2}(?![\d.])"),
}

SECRETOS = {
    "clave con prefijo de proveedor": re.compile(
        r"\b(?:sk|hf|ghp|gho|xoxb|xoxp)[-_][A-Za-z0-9_-]{16,}"
    ),
    "clave de AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Un nombre que acaba en password, secret, token o api_key, y un valor literal largo entre
    # comillas. En código de LLMs, "tokens = ..." es lo normal: sin las comillas y la longitud,
    # la regla salta en cada cuenta de tokens (lección 6.06).
    "asignación de secreto": re.compile(
        r"(?i)\b\w*(?:password|passwd|secret|token|api_?key)\s*[=:]\s*['\"][\w/+=.-]{16,}['\"]"
    ),
}


def dni_valido(numero: str, letra: str) -> bool:
    """La letra del DNI es el número módulo 23: descarta números que solo lo parecen."""
    return LETRAS_DNI[int(numero) % 23] == letra


def encontrar(texto: str) -> list[tuple[str, str]]:
    """Los datos personales del texto: [(tipo, valor)], sin solapes."""
    hallados, ocupado = [], []
    for tipo, patron in PATRONES.items():
        for m in patron.finditer(texto):
            if any(m.start() < fin and inicio < m.end() for inicio, fin in ocupado):
                continue
            if tipo == "DNI" and not dni_valido(m[1], m[2]):
                continue
            if tipo == "NIE" and not dni_valido(str("XYZ".index(m[1])) + m[2], m[3]):
                continue
            hallados.append((tipo, m.group(0)))
            ocupado.append((m.start(), m.end()))
    return hallados


def redactar(texto: str) -> str:
    """Sustituye cada dato personal por su tipo: "escribe a [EMAIL]"."""
    for tipo, valor in encontrar(texto):
        texto = texto.replace(valor, f"[{tipo}]")
    return texto


def buscar_secretos(texto: str) -> list[tuple[str, str]]:
    """[(tipo, línea)] de las líneas que parecen contener un secreto, una vez por línea."""
    hallados = []
    for linea in texto.splitlines():
        tipo = next((t for t, patron in SECRETOS.items() if patron.search(linea)), None)
        if tipo:
            hallados.append((tipo, linea.strip()))
    return hallados

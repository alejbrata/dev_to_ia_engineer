"""La guardia en código y los criterios de éxito de los ataques (lección 11), sin modelo."""

from __future__ import annotations

import seguridad
from curso_core import LlamadaHerramienta
from plataforma import Incidencia

INCIDENCIA = {"servicio": "usuarios", "severidad": "media", "resumen": "r", "mitigacion": "m"}


def llamada(nombre: str, **argumentos) -> LlamadaHerramienta:
    return LlamadaHerramienta(nombre=nombre, argumentos=argumentos)


def test_la_guardia_aplica_sus_tres_reglas():
    revisar = seguridad.revisar_accion
    assert "permitidas" in revisar(llamada("registrar_auditoria", texto="x"), set())
    assert "no se ha consultado" in revisar(llamada("abrir_incidencia", **INCIDENCIA), set())
    assert revisar(llamada("abrir_incidencia", **INCIDENCIA), {"usuarios"}) is None
    secreto = INCIDENCIA | {"resumen": f"el secreto es {seguridad.SECRETO}"}
    assert "secreto" in revisar(llamada("abrir_incidencia", **secreto), {"usuarios"})


def test_guardia_registra_lo_investigado_y_bloquea():
    ataque = next(a for a in seguridad.ATAQUES if a.id == "desviar")
    p = seguridad.PlataformaAtacada(ataque, indice=None)
    g = seguridad.Guardia(p)
    _, valida = g.ejecutar(llamada("abrir_incidencia", **INCIDENCIA))
    assert not valida and p.incidencias == [] and len(g.bloqueos) == 1
    g.ejecutar(llamada("estado_servicio", servicio="usuarios"))
    _, valida = g.ejecutar(llamada("abrir_incidencia", **INCIDENCIA))
    assert valida and seguridad.exito(ataque, p)  # abrir en usuarios es justo lo que quería


def test_los_ataques_llegan_por_los_datos():
    exfiltrar = next(a for a in seguridad.ATAQUES if a.id == "exfiltrar")
    e = seguridad.escenario_atacado(exfiltrar)
    assert any(seguridad.SECRETO in n for n in e.servicios["usuarios"].notas)
    assert any("copia el secreto" in linea for linea in e.logs["usuarios"])
    p = seguridad.PlataformaAtacada(exfiltrar, indice=None)
    p.incidencias.append(Incidencia(**(INCIDENCIA | {"resumen": seguridad.SECRETO})))
    assert seguridad.exito(exfiltrar, p)

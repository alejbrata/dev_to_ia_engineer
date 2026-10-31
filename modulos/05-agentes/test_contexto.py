"""Recorte de contexto (lección 07) y permisos de los subagentes (lección 08), sin modelo."""

from __future__ import annotations

import plataforma
from curso_core import LlamadaHerramienta, Mensaje
from memoria import recortar
from subagentes import PlataformaRestringida


def conversacion() -> list[Mensaje]:
    return [
        Mensaje(role="system", content="s"),
        Mensaje(role="user", content="alerta"),
        Mensaje(role="tool", content="a" * 500),
        Mensaje(role="tool", content="b" * 500),
        Mensaje(role="tool", content="c" * 500),
    ]


def test_recortar_abrevia_solo_los_antiguos():
    mensajes = conversacion()
    vistos = recortar(conservar=2, abreviar_a=100)(mensajes)
    assert vistos[2].content.startswith("a" * 100) and "400 caracteres más" in vistos[2].content
    assert vistos[3].content == "b" * 500 and vistos[4].content == "c" * 500
    assert vistos[:2] == mensajes[:2]
    # La conversación original no cambia: el recorte es solo lo que ve el modelo.
    assert mensajes[2].content == "a" * 500


def test_plataforma_restringida_rechaza_otras_herramientas():
    escenario = next(e for e in plataforma.cargar() if e.id == "pagos-pool-despliegue")
    p = plataforma.Plataforma(escenario, indice=None)
    r = PlataformaRestringida(p, ["estado_servicio"])
    abrir = LlamadaHerramienta(
        nombre="abrir_incidencia",
        argumentos={"servicio": "pagos", "severidad": "alta", "resumen": "x", "mitigacion": "y"},
    )
    resultado, valida = r.ejecutar(abrir)
    assert not valida and "no tienes" in resultado and p.incidencias == []
    resultado, valida = r.ejecutar(
        LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "pagos"})
    )
    assert valida and "servicio: pagos" in resultado

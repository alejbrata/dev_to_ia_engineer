"""Reintentos, idempotencia y checkpoints de conversación (lección 13), sin modelo."""

from __future__ import annotations

import aguante
import plataforma
from curso_core import LlamadaHerramienta, Mensaje

ESTADO = LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "pagos"})
ABRIR = LlamadaHerramienta(
    nombre="abrir_incidencia",
    argumentos={"servicio": "pagos", "severidad": "critica", "resumen": "r", "mitigacion": "m"},
)


def escenario():
    return next(e for e in plataforma.cargar() if e.id == "pagos-pool-despliegue")


def test_reintenta_solo_lecturas_transitorias():
    p = plataforma.Plataforma(escenario(), indice=None)
    siempre_falla = aguante.Inestable(p, prob=1.0, semilla=0)
    r = aguante.ConReintentos(siempre_falla, intentos=3)
    resultado, valida = r.ejecutar(ESTADO)
    assert not valida and resultado.startswith(aguante.TRANSITORIO)
    assert siempre_falla.fallos == 3 and r.reintentos == 2
    # Las acciones no pasan por los fallos ni se reintentan.
    _, valida = r.ejecutar(ABRIR)
    assert valida and len(p.incidencias) == 1


def test_la_clave_de_idempotencia_evita_duplicados(tmp_path):
    for idempotente, esperadas in [(False, 2), (True, 1)]:
        sistema = aguante.SistemaIncidencias(tmp_path / f"inc-{idempotente}.json")
        primera = aguante.PlataformaPersistente(escenario(), None, sistema, idempotente)
        primera.ejecutar(ABRIR)
        # Otro proceso, tras una caída, vuelve a abrir la misma incidencia.
        segunda = aguante.PlataformaPersistente(escenario(), None, sistema, idempotente)
        assert len(segunda.incidencias) == 1  # la lee del gestor externo
        segunda.ejecutar(ABRIR)
        assert len(sistema.todas()) == esperadas


def test_checkpoint_de_conversacion(tmp_path):
    ck = aguante.CheckpointConversacion(tmp_path / "c.json")
    assert ck.cargar() is None
    mensajes = [
        Mensaje(role="user", content="alerta"),
        Mensaje(role="assistant", llamadas=[ESTADO]),
        Mensaje(role="tool", content="estado: caido", respuesta_a=ESTADO),
    ]
    ck.guardar(mensajes)
    assert ck.cargar() == mensajes

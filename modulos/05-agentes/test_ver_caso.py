"""ver_caso.py sobre resultados grabados, y --rol de las prácticas, sin modelo."""

from __future__ import annotations

import os
import sys

import agente
import pytest
import ver_caso
from curso_core import ClienteLLM


def ejecutar(monkeypatch, capsys, *argumentos: str) -> str:
    monkeypatch.setattr(sys, "argv", ["ver_caso.py", *argumentos])
    assert ver_caso.main() == 0
    return capsys.readouterr().out


def test_lista_los_casos_y_muestra_uno(monkeypatch, capsys):
    lista = ejecutar(monkeypatch, capsys, "memoria-completo")
    assert "pagos-pool-despliegue" in lista and "de 14 bien" in lista
    caso = ejecutar(monkeypatch, capsys, "memoria-completo", "pagos-pool-despliegue")
    assert "Herramientas que pidió" in caso and "→ estado_servicio" in caso


def test_un_plan_se_muestra_campo_a_campo(monkeypatch, capsys):
    salida = ejecutar(monkeypatch, capsys, "comite", "comité|agente|brecha-datos")
    assert "severidad: " in salida and "tecnico: " in salida


def test_un_fichero_que_no_existe_dice_cuales_hay():
    with pytest.raises(SystemExit, match="Disponibles: .*memoria-completo"):
        ver_caso.ruta("no-existe")


def test_rol_redirige_el_agente_y_separa_los_resultados(monkeypatch, tmp_path):
    monkeypatch.setenv("CURSO_ROLES", "")  # y pytest la restaura al terminar
    assert agente.usar_rol("agente", tmp_path) == tmp_path
    assert os.environ["CURSO_ROLES"] == ""
    assert agente.usar_rol("chat_openai", tmp_path) == tmp_path / "chat_openai"
    cliente = ClienteLLM()
    assert cliente.config.resolver("agente") == cliente.config.resolver("chat_openai")

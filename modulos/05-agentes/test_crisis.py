"""El supuesto de crisis del cierre (lección 15), sin modelo: anclaje, puntuación y plan."""

from __future__ import annotations

import crisis
from crisis import Encargo, PlanEncargos, PlanRespuesta
from curso_core import LlamadaHerramienta


def test_lo_esperado_sale_de_las_politicas():
    assert crisis.problemas_de_anclaje(crisis.cargar()) == []


def test_puntuar_cuenta_lo_que_cubre_el_plan():
    c = next(x for x in crisis.cargar() if x.id == "brecha-datos")
    plan = PlanRespuesta(
        severidad="critica",
        tecnico=["Retirar el acceso público al contenedor", "Rotar las credenciales"],
        legal=["Avisar al DPO", "Notificar a la AEPD en un plazo de 72 horas"],
        negocio=[],
        comunicacion=[],
    )
    p = crisis.puntuar(c, plan)
    assert (p.cubiertas, p.total) == (5, 6) and p.faltan == ["comunicacion: afectados"]
    assert crisis.puntuar(c, None).cubiertas == 0


def test_el_plan_de_encargos_se_valida_y_se_ordena():
    plan = PlanEncargos(
        encargos=[
            Encargo(id="e2", especialista="legal", pregunta="?", depende_de=["e1"]),
            Encargo(id="e1", especialista="tecnico", pregunta="?"),
        ]
    )
    assert crisis.problemas_plan(plan) == [] and crisis.orden(plan) == ["e1", "e2"]
    ciclo = PlanEncargos(
        encargos=[
            Encargo(id="e1", especialista="tecnico", pregunta="?", depende_de=["e2"]),
            Encargo(id="e2", especialista="legal", pregunta="?", depende_de=["e1"]),
        ]
    )
    assert crisis.problemas_plan(ciclo) == ["hay un ciclo en las dependencias"]
    roto = PlanEncargos(
        encargos=[Encargo(id="e1", especialista="negocio", pregunta="?", depende_de=["x"])]
    )
    assert "no existe" in crisis.problemas_plan(roto)[0]


def test_el_error_del_plan_dice_que_campo_falla():
    c = next(x for x in crisis.cargar() if x.id == "brecha-datos")
    p = crisis.PlataformaCrisis(c, indice_docs=None)
    args = {"severidad": "alta", "tecnico": [], "legal": [], "negocio": []}
    args["comunicacion"] = [{"canal": "email", "mensaje": "..."}]
    texto, valida = p.ejecutar(LlamadaHerramienta(nombre="proponer_plan", argumentos=args))
    assert not valida and "(comunicacion.0)" in texto and p.plan is None

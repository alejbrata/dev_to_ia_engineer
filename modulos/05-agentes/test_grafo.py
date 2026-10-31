"""El motor de grafos sin modelo: aristas, ciclos, checkpoints e interrupciones."""

from __future__ import annotations

import pytest
from grafo import FIN, Checkpoints, ErrorGrafo, Grafo
from pydantic import BaseModel


class Contador(BaseModel):
    n: int = 0
    aprobado: bool = False
    hecho: bool = False


def grafo_contador(hasta: int = 3) -> Grafo[Contador]:
    g = Grafo(Contador, inicio="sumar")
    g.nodo("sumar", lambda e: {"n": e.n + 1})
    g.nodo("terminar", lambda e: {"hecho": True})
    g.arista_condicional(
        "sumar", lambda e: "sumar" if e.n < hasta else "terminar", {"sumar", "terminar"}
    )
    g.arista("terminar", FIN)
    return g


def test_ciclo_hasta_la_condicion(tmp_path):
    r = grafo_contador().ejecutar(Contador(), hilo="h", checkpoints=Checkpoints(tmp_path))
    assert r.estado.n == 3 and r.estado.hecho
    assert [p.nodo for p in r.pasos] == ["sumar", "sumar", "sumar", "terminar"]


def test_limite_de_pasos(tmp_path):
    with pytest.raises(ErrorGrafo, match="más de 5 pasos"):
        grafo_contador(hasta=100).ejecutar(
            Contador(), hilo="h", checkpoints=Checkpoints(tmp_path), max_pasos=5
        )


def test_interrumpe_y_reanuda_con_cambios(tmp_path):
    ck = Checkpoints(tmp_path)
    g = grafo_contador()
    r = g.ejecutar(Contador(), hilo="h", checkpoints=ck, interrumpir_antes=frozenset({"terminar"}))
    assert r.pendiente == "terminar" and not r.estado.hecho
    r = g.ejecutar(
        None,
        hilo="h",
        checkpoints=ck,
        interrumpir_antes=frozenset({"terminar"}),
        cambios={"aprobado": True},
    )
    assert r.pendiente is None and r.estado.hecho and r.estado.aprobado
    assert [p.nodo for p in r.pasos] == ["terminar"]


def test_reanuda_tras_una_caida(tmp_path):
    ck = Checkpoints(tmp_path)
    g = grafo_contador()
    llamadas = []

    def terminar_que_cae(e):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError("caída")
        return {"hecho": True}

    g.nodo("terminar", terminar_que_cae)
    with pytest.raises(RuntimeError):
        g.ejecutar(Contador(), hilo="h", checkpoints=ck)
    r = g.ejecutar(None, hilo="h", checkpoints=ck)
    assert r.estado.n == 3 and r.estado.hecho
    assert [p.nodo for p in r.pasos] == ["terminar"]


def test_valida_el_grafo_y_las_actualizaciones(tmp_path):
    g = Grafo(Contador, inicio="sumar")
    g.nodo("sumar", lambda e: {"m": 1})
    g.arista("sumar", "no_existe")
    with pytest.raises(ErrorGrafo, match="'no_existe', que no existe"):
        g.ejecutar(Contador(), hilo="h", checkpoints=Checkpoints(tmp_path))
    g.arista("sumar", FIN)
    with pytest.raises(ErrorGrafo, match="campos que el estado no tiene"):
        g.ejecutar(Contador(), hilo="h", checkpoints=Checkpoints(tmp_path))


def test_condicion_con_destino_no_declarado(tmp_path):
    g = Grafo(Contador, inicio="sumar")
    g.nodo("sumar", lambda e: {"n": 1})
    g.arista_condicional("sumar", lambda e: "otro", {FIN})
    with pytest.raises(ErrorGrafo, match="no es uno de sus destinos"):
        g.ejecutar(Contador(), hilo="h", checkpoints=Checkpoints(tmp_path))

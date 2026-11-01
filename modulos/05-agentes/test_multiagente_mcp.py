"""El coordinador multiagente (lección 09) y el servidor MCP (lección 10), sin modelo."""

from __future__ import annotations

import json

import anyio
import plataforma
import servidor_mcp
from curso_core import LlamadaHerramienta
from mcp import Client
from multiagente import Pizarra, PlataformaInvestigador, Propuesta, Revision, decision_final

PROPUESTA = Propuesta(
    abrir=True, servicio="pagos", severidad="alta", resumen="pool lleno", mitigacion="revertir"
)


def revision(**cambios) -> Revision:
    base = {
        "de_acuerdo": False,
        "abrir": True,
        "severidad": "critica",
        "mitigacion": "volver a la versión anterior",
        "motivo": "pérdida de dinero",
    }
    return Revision(**(base | cambios))


def test_el_coordinador_aplica_la_correccion_del_revisor():
    final = decision_final(PROPUESTA, revision())
    assert final.severidad == "critica" and final.mitigacion == "volver a la versión anterior"
    assert decision_final(PROPUESTA, revision(de_acuerdo=True)) == PROPUESTA
    assert decision_final(PROPUESTA, None) == PROPUESTA
    # Sin severidad del revisor, se queda la propuesta: sin ella no se abriría nada.
    assert decision_final(PROPUESTA, revision(severidad=None)).severidad == "alta"
    assert decision_final(PROPUESTA, revision(abrir=False)).abrir is False


def test_el_investigador_propone_pero_no_abre():
    escenario = next(e for e in plataforma.cargar() if e.id == "pagos-pool-despliegue")
    p = plataforma.Plataforma(escenario, indice=None)
    pizarra = Pizarra(alerta=escenario.alerta)
    inv = PlataformaInvestigador(p, pizarra)
    _, valida = inv.ejecutar(
        LlamadaHerramienta(nombre="abrir_incidencia", argumentos=PROPUESTA.model_dump())
    )
    assert not valida and p.incidencias == []
    inv.ejecutar(LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "pagos"}))
    inv.ejecutar(
        LlamadaHerramienta(nombre="proponer_incidencia", argumentos=PROPUESTA.model_dump())
    )
    assert [e.herramienta for e in pizarra.evidencias] == ["estado_servicio"]
    assert pizarra.propuesta == PROPUESTA and p.incidencias == []


def test_servidor_mcp_en_memoria():
    servidor = servidor_mcp.crear("pagos-pool-despliegue", indice=object())

    async def probar():
        async with Client(servidor) as c:
            nombres = [t.name for t in (await c.list_tools()).tools]
            assert nombres == [
                "estado_servicio",
                "buscar_logs",
                "buscar_documentacion",
                "abrir_incidencia",
            ]
            r = await c.call_tool("estado_servicio", {"servicio": "facturacion"})
            assert r.is_error
            r = await c.call_tool("abrir_incidencia", PROPUESTA.model_dump(exclude={"abrir"}))
            assert not r.is_error and "INC-1" in r.content[0].text
            leido = await c.read_resource("plataforma://incidencias")
            return json.loads(leido.contents[0].text)

    incidencias = anyio.run(probar)
    assert incidencias[0]["severidad"] == "alta"

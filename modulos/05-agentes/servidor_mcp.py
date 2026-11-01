"""Las herramientas de la plataforma como servidor MCP (lección 10).

Expone, para un escenario, las cuatro herramientas del agente de guardia con las mismas
descripciones que la versión 2 de la lección 02, y las incidencias abiertas como recurso
(`plataforma://incidencias`), para que quien lo use pueda comprobar el estado final.

Habla MCP por stdio: lo lanza el cliente como subproceso y se comunican por su entrada y su
salida estándar. Por eso este proceso no puede escribir nada en stdout: es el canal del
protocolo. Los avisos van a stderr.

Uso (normalmente lo lanza el cliente, no tú):
`uv run python modulos/05-agentes/servidor_mcp.py --escenario pagos-pool-despliegue`
"""

from __future__ import annotations

import argparse
import json
from typing import Annotated

import plataforma
from curso_core import ClienteLLM
from mcp.server import MCPServer
from plataforma import (
    HERRAMIENTAS,
    ArgsBuscar,
    ArgsBuscarV2,
    ArgsLogs,
    ArgsLogsV2,
    ArgsServicio,
    Incidencia,
    IncidenciaV2,
    Servicio,
    Severidad,
)
from pydantic import Field

DESCRIPCION = {h.nombre: h.descripcion for h in HERRAMIENTAS}


def campo(modelo, nombre: str) -> Field:
    """La descripción de un argumento, la misma de la versión 2 de la lección 02."""
    return Field(description=modelo.model_fields[nombre].description)


def crear(escenario_id: str, indice=None) -> MCPServer:
    """El servidor para un escenario. Sin `indice`, construye el de la documentación."""
    escenario = next(e for e in plataforma.cargar() if e.id == escenario_id)
    indice = indice if indice is not None else plataforma.indice_documentacion(ClienteLLM())
    p = plataforma.Plataforma(escenario, indice)
    servidor = MCPServer(
        "plataforma-guardia",
        instructions="Herramientas de la plataforma de comercio electrónico del curso.",
    )

    @servidor.tool(description=DESCRIPCION["estado_servicio"], structured_output=False)
    def estado_servicio(servicio: Servicio) -> str:
        return p.estado_servicio(ArgsServicio(servicio=servicio))

    @servidor.tool(description=DESCRIPCION["buscar_logs"], structured_output=False)
    def buscar_logs(
        servicio: Servicio, texto: Annotated[str, campo(ArgsLogsV2, "texto")] = ""
    ) -> str:
        return p.buscar_logs(ArgsLogs(servicio=servicio, texto=texto))

    @servidor.tool(description=DESCRIPCION["buscar_documentacion"], structured_output=False)
    def buscar_documentacion(consulta: Annotated[str, campo(ArgsBuscarV2, "consulta")]) -> str:
        return p.buscar_documentacion(ArgsBuscar(consulta=consulta))

    @servidor.tool(description=DESCRIPCION["abrir_incidencia"], structured_output=False)
    def abrir_incidencia(
        servicio: Annotated[Servicio, campo(IncidenciaV2, "servicio")],
        severidad: Annotated[Severidad, campo(IncidenciaV2, "severidad")],
        resumen: Annotated[str, campo(IncidenciaV2, "resumen")],
        mitigacion: Annotated[str, campo(IncidenciaV2, "mitigacion")],
    ) -> str:
        return p.abrir_incidencia(
            Incidencia(
                servicio=servicio, severidad=severidad, resumen=resumen, mitigacion=mitigacion
            )
        )

    @servidor.resource("plataforma://incidencias", mime_type="application/json")
    def incidencias() -> str:
        """Las incidencias abiertas en este escenario."""
        return json.dumps([i.model_dump() for i in p.incidencias], ensure_ascii=False)

    return servidor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--escenario", required=True)
    crear(parser.parse_args().escenario).run()  # stdio

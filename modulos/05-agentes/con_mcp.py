"""El agente de guardia con sus herramientas servidas por MCP (lección 10).

1. La conexión: versión del protocolo, herramientas que anuncia el servidor y si sus
   esquemas coinciden con los de la lección 02.
2. Tres peticiones a mano: una herramienta, una llamada con un argumento inválido y el
   recurso de incidencias.
3. El mismo agente de siempre, con las herramientas por MCP, en los escenarios de
   desarrollo, frente al agente con las herramientas en su propio proceso.
4. Lo que cuesta el protocolo: arrancar el servidor y cada llamada.

El agente con las herramientas en su proceso es el de memoria_y_contexto.py. Con --grabadas
no llama al modelo. Uso: `uv run python modulos/05-agentes/con_mcp.py [--grabadas]`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import median

import agente
import anyio
import anyio.from_thread
import anyio.to_thread
import plataforma
from curso_core import ClienteLLM, Herramienta, LlamadaHerramienta
from curso_core.evals import Informe, ResultadoCaso, comparar, prueba_mcnemar
from mcp import Client, StdioServerParameters
from mcp.types import TextContent

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
SERVIDOR = AQUI / "servidor_mcp.py"
ROL = "agente"
OPCIONES = agente.OPCIONES.model_copy(update={"razonar": False})
EJEMPLO = "pagos-pool-despliegue"
LLAMADAS_MEDIDA = 50


def parametros(escenario_id: str) -> StdioServerParameters:
    """Cómo lanzar el servidor: el mismo Python del entorno, con el escenario."""
    return StdioServerParameters(
        command=sys.executable, args=[str(SERVIDOR), "--escenario", escenario_id]
    )


def texto(resultado) -> str:
    return "\n".join(b.text for b in resultado.content if isinstance(b, TextContent))


def sin_titulos(esquema):
    """El esquema sin los "title", que Pydantic pone distintos según cómo se genera."""
    if isinstance(esquema, dict):
        return {k: sin_titulos(v) for k, v in esquema.items() if k != "title"}
    return esquema


class PlataformaMCP:
    """Lo que ve el bucle de agente.py: cada herramienta es una llamada tools/call."""

    def __init__(self, client: Client, escenario):
        self.client = client
        self.escenario = escenario
        self.milisegundos: list[float] = []

    def ejecutar(self, llamada: LlamadaHerramienta) -> tuple[str, bool]:
        inicio = time.perf_counter()
        # El bucle es síncrono y corre en un hilo; la sesión MCP es asíncrona.
        r = anyio.from_thread.run(self.client.call_tool, llamada.nombre, llamada.argumentos)
        self.milisegundos.append((time.perf_counter() - inicio) * 1000)
        return texto(r), not r.is_error


async def conexion() -> dict:
    inicio = time.perf_counter()
    async with Client(parametros(EJEMPLO)) as c:
        arranque = time.perf_counter() - inicio
        herramientas = (await c.list_tools()).tools
        locales = {h.nombre: h.parametros for h in plataforma.HERRAMIENTAS}
        distintas = [
            t.name
            for t in herramientas
            if sin_titulos(t.input_schema) != sin_titulos(locales.get(t.name, {}))
        ]
        bien = await c.call_tool("estado_servicio", {"servicio": "pagos"})
        mal = await c.call_tool("estado_servicio", {"servicio": "facturacion"})
        recurso = await c.read_resource("plataforma://incidencias")

        inicio = time.perf_counter()
        for _ in range(LLAMADAS_MEDIDA):
            await c.call_tool("estado_servicio", {"servicio": "pagos"})
        ms_mcp = (time.perf_counter() - inicio) * 1000 / LLAMADAS_MEDIDA
        return {
            "version": c.protocol_version,
            "servidor": c.server_info.name,
            "herramientas": [t.name for t in herramientas],
            "esquema_abrir": herramientas[-1].input_schema["properties"]["severidad"],
            "esquemas_distintos": distintas,
            "bien": {"is_error": bien.is_error, "texto": texto(bien)},
            "mal": {"is_error": mal.is_error, "texto": texto(mal)},
            "recurso": recurso.contents[0].text,
            "arranque_s": round(arranque, 1),
            "ms_por_llamada_mcp": round(ms_mcp, 2),
        }


async def con_agente(cliente: ClienteLLM, escenario) -> ResultadoCaso:
    inicio = time.perf_counter()
    async with Client(parametros(escenario.id)) as c:
        arranque = time.perf_counter() - inicio
        herramientas = [
            Herramienta(nombre=t.name, descripcion=t.description or "", parametros=t.input_schema)
            for t in (await c.list_tools()).tools
        ]
        p = PlataformaMCP(c, escenario)
        ej = await anyio.to_thread.run_sync(
            lambda: agente.ejecutar(
                cliente, p, rol=ROL, opciones=OPCIONES, herramientas=herramientas
            )
        )
        incidencias = json.loads(
            (await c.read_resource("plataforma://incidencias")).contents[0].text
        )
    # El estado final lo comprueba el mismo código de siempre, con lo que dice el servidor.
    local = plataforma.Plataforma(escenario, indice=None)
    local.incidencias = [plataforma.Incidencia(**i) for i in incidencias]
    comprobacion = plataforma.comprobar(local)
    return ResultadoCaso(
        caso=escenario.id,
        ok=comprobacion.ok,
        salida=ej.respuesta,
        detalle={
            "motivo": comprobacion.motivo,
            "pasos": len(ej.pasos),
            "tokens": ej.tokens,
            "segundos": round(ej.segundos, 1),
            "arranque_s": round(arranque, 1),
            "ms_herramientas": [round(x, 1) for x in p.milisegundos],
            "usos": [f"{u.nombre}({u.argumentos})" for u in ej.usos],
        },
    )


def ms_por_llamada_local() -> float:
    escenario = next(e for e in plataforma.cargar() if e.id == EJEMPLO)
    p = plataforma.Plataforma(escenario, indice=None)
    llamada = LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "pagos"})
    inicio = time.perf_counter()
    for _ in range(LLAMADAS_MEDIDA):
        p.ejecutar(llamada)
    return (time.perf_counter() - inicio) * 1000 / LLAMADAS_MEDIDA


async def medir(escenarios) -> tuple[dict, Informe]:
    datos = await conexion()
    cliente = ClienteLLM()
    cliente.descargar_modelo(ROL)
    resultados = [await con_agente(cliente, e) for e in escenarios]
    return datos, Informe(version="mcp", resultados=resultados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    args = parser.parse_args()
    escenarios = [e for e in plataforma.cargar() if e.particion == "desarrollo"]
    ruta, ruta_datos = RESULTADOS / "mcp.jsonl", RESULTADOS / "mcp-conexion.json"

    if args.grabadas:
        informe = Informe.cargar(ruta)
        datos = json.loads(ruta_datos.read_text(encoding="utf-8"))
    else:
        datos, informe = anyio.run(medir, escenarios)
        datos["ms_por_llamada_local"] = round(ms_por_llamada_local(), 3)
        informe.guardar(ruta)
        ruta_datos.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"1. Conexión con el servidor ({datos['servidor']})")
    print(f"   protocolo: {datos['version']}")
    print(f"   herramientas: {', '.join(datos['herramientas'])}")
    distintas = datos["esquemas_distintos"] or "ninguno"
    print(f"   esquemas distintos de los de la lección 02 (sin contar títulos): {distintas}")
    severidad = json.dumps(datos["esquema_abrir"], ensure_ascii=False)
    print(f"   abrir_incidencia, argumento severidad: {severidad[:120]}…")

    print("\n2. Tres peticiones a mano")
    print(f"   tools/call estado_servicio(pagos) → is_error={datos['bien']['is_error']}")
    print(
        f"      {datos['bien']['texto'].splitlines()[1]} · {datos['bien']['texto'].splitlines()[2]}"
    )
    print(f"   tools/call estado_servicio(facturacion) → is_error={datos['mal']['is_error']}")
    print(f"      {datos['mal']['texto'].splitlines()[0]}")
    print(f"   resources/read plataforma://incidencias → {datos['recurso']}")

    n = len(escenarios)
    rs = informe.resultados
    completo = Informe.cargar(RESULTADOS / "memoria-completo.jsonl")
    ids = {e.id for e in escenarios}
    local = Informe(version="local", resultados=[r for r in completo.resultados if r.caso in ids])
    print(f"\n3. El agente en los {n} escenarios de desarrollo")
    print(f"   {'':26} {'estado ok':>9} {'pasos':>6} {'tokens':>7} {'s/escenario':>11}")
    for nombre, inf in [("herramientas en el proceso", local), ("herramientas por MCP", informe)]:
        print(
            f"   {nombre:26} {inf.aciertos:>5} de {n} "
            f"{sum(r.detalle['pasos'] for r in inf.resultados):>6} "
            f"{sum(r.detalle['tokens'] for r in inf.resultados):>7} "
            f"{median(r.detalle['segundos'] for r in inf.resultados):>11.0f}"
        )
    c = comparar(local, informe)
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   MCP gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")
    for r in rs:
        if not r.ok:
            print(f"   {r.caso}: {r.detalle['motivo']}")

    ms = [x for r in rs for x in r.detalle["ms_herramientas"]]
    print("\n4. Lo que cuesta el protocolo")
    print(f"   arrancar el servidor (incluye construir el índice): {datos['arranque_s']} s")
    print(
        f"   una llamada a estado_servicio: {datos['ms_por_llamada_local']} ms en el proceso, "
        f"{datos['ms_por_llamada_mcp']} ms por MCP"
    )
    print(
        f"   llamadas del agente por MCP: {len(ms)}, mediana {median(ms):.0f} ms "
        f"(buscar_documentacion incluye calcular el embedding)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

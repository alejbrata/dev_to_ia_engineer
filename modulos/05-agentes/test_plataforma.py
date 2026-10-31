import plataforma
from curso_core import LlamadaHerramienta
from plataforma import Incidencia, Plataforma


class IndiceFalso:
    """Un índice que no llama a ningún modelo: devuelve siempre el mismo fragmento."""

    def buscar(self, consulta: str, k: int = 3):
        from curso_core.rag import Fragmento, Resultado

        f = Fragmento(
            id="runbook-pagos-conexiones#2",
            doc="runbook-pagos-conexiones",
            titulo="Runbook > Mitigación",
            texto="Vuelve a la versión anterior.",
        )
        return [Resultado(fragmento=f, puntuacion=1.0)]


def escenario(id_: str) -> plataforma.Escenario:
    return {e.id: e for e in plataforma.cargar()}[id_]


def test_los_escenarios_estan_anclados_al_corpus() -> None:
    escenarios = plataforma.cargar()
    assert plataforma.problemas_de_anclaje(escenarios, plataforma.corpus.documentos()) == []
    assert len({e.id for e in escenarios}) == len(escenarios)
    assert {e.particion for e in escenarios} == {"desarrollo", "prueba"}


def test_comprobar_mira_el_estado_final_no_lo_que_dice_el_agente() -> None:
    p = Plataforma(escenario("pagos-pool-despliegue"), IndiceFalso())
    assert plataforma.comprobar(p).motivo == "no abrió la incidencia"
    p.abrir_incidencia(
        Incidencia(
            servicio="pagos",
            severidad="critica",
            resumen="too many connections tras desplegar",
            mitigacion="Volver a la versión anterior",
        )
    )
    assert plataforma.comprobar(p).ok
    p.abrir_incidencia(
        Incidencia(
            servicio="pagos", severidad="critica", resumen="otra", mitigacion="versión anterior"
        )
    )
    assert "2 incidencias" in plataforma.comprobar(p).motivo


def test_comprobar_severidad_y_mitigacion() -> None:
    p = Plataforma(escenario("pagos-pool-despliegue"), IndiceFalso())
    p.abrir_incidencia(
        Incidencia(
            servicio="pagos", severidad="media", resumen="pool lleno", mitigacion="Monitorizar"
        )
    )
    motivo = plataforma.comprobar(p).motivo
    assert "severidad media" in motivo and "versión anterior" in motivo


def test_falsa_alarma_sin_incidencia() -> None:
    p = Plataforma(escenario("catalogo-replica-normal"), IndiceFalso())
    assert plataforma.comprobar(p).ok
    p.abrir_incidencia(
        Incidencia(servicio="catalogo", severidad="baja", resumen="r", mitigacion="m")
    )
    assert not plataforma.comprobar(p).ok


def test_las_herramientas_devuelven_errores_al_modelo() -> None:
    p = Plataforma(escenario("pagos-pool-despliegue"), IndiceFalso())
    salida, valida = p.ejecutar(
        LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "facturacion"})
    )
    assert not valida and salida.startswith("Error en los argumentos (servicio)")
    salida, valida = p.ejecutar(LlamadaHerramienta(nombre="reiniciar", argumentos={}))
    assert not valida and "no existe la herramienta" in salida
    salida, valida = p.ejecutar(
        LlamadaHerramienta(
            nombre="buscar_logs", argumentos={"servicio": "pagos", "texto": "TOO MANY"}
        )
    )
    assert valida and "too many connections" in salida
    p.ejecutar(LlamadaHerramienta(nombre="buscar_documentacion", argumentos={"consulta": "x"}))
    assert p.consultados == ["runbook-pagos-conexiones"]

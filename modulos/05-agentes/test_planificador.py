from planificador import Plan, Tarea, orden_topologico, problemas, sustituir


def tarea(id_: str, herramienta: str, argumentos: dict, depende_de=()) -> Tarea:
    return Tarea(
        id=id_,
        herramienta=herramienta,
        argumentos=argumentos,
        depende_de=list(depende_de),
        para_que="",
    )


def test_un_plan_valido_se_ordena_respetando_las_dependencias() -> None:
    plan = Plan(
        tareas=[
            tarea("t3", "buscar_documentacion", {"consulta": "${t2}"}, ["t2"]),
            tarea("t1", "estado_servicio", {"servicio": "pagos"}),
            tarea("t2", "buscar_logs", {"servicio": "pagos"}, ["t1"]),
        ]
    )
    assert problemas(plan) == []
    assert orden_topologico(plan) == ["t1", "t2", "t3"]


def test_detecta_lo_que_impide_ejecutar_el_plan() -> None:
    plan = Plan(
        tareas=[
            tarea("t1", "reiniciar", {}),
            tarea("t2", "estado_servicio", {"servicio": "facturacion"}),
            tarea("t3", "buscar_documentacion", {"consulta": "${t1}"}),
            tarea("t4", "buscar_logs", {"servicio": "pagos"}, ["t9"]),
            tarea("t5", "abrir_incidencia", {}),
        ]
    )
    errores = " | ".join(problemas(plan))
    assert "t1: la herramienta 'reiniciar' no está disponible" in errores
    assert "t2: argumentos de estado_servicio no válidos (servicio)" in errores
    assert "t3: usa ${t1} sin depender de t1" in errores
    assert "t4: depende de 't9', que no existe" in errores
    assert "t5: la herramienta 'abrir_incidencia' no está disponible" in errores


def test_detecta_ciclos() -> None:
    plan = Plan(
        tareas=[
            tarea("a", "buscar_logs", {"servicio": "pagos"}, ["b"]),
            tarea("b", "buscar_logs", {"servicio": "pagos"}, ["a"]),
        ]
    )
    assert orden_topologico(plan) is None
    assert problemas(plan) == ["las dependencias forman un ciclo"]


def test_sustituye_las_referencias_por_el_resultado() -> None:
    args = sustituir(
        {"consulta": "runbook de ${t2}", "servicio": "pagos"},
        {"t2": "ERROR too many connections\nWARN pool 194/200\nINFO otra\nINFO más"},
    )
    assert args == {
        "consulta": "runbook de ERROR too many connections WARN pool 194/200 INFO otra",
        "servicio": "pagos",
    }

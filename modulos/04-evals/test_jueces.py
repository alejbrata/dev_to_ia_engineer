import jueces


def test_las_etiquetas_estan_ancladas() -> None:
    """Los apoyos están literalmente en el contexto y las afirmaciones, en la respuesta."""
    todos = jueces.fragmentos()
    assert jueces.problemas_de_etiquetas(jueces.cargar(), todos) == []


def test_hay_etiquetas_de_las_dos_clases() -> None:
    etiquetas = jueces.cargar()
    assert {e.fiel for e in etiquetas} == {True, False}
    assert len({e.id for e in etiquetas}) == len(etiquetas)


def test_cita_valida() -> None:
    ctx = "[1] Runbook > Mitigación\nReinicia PgBouncer de forma ordenada, una réplica cada vez."
    assert jueces.cita_valida("reinicia pgbouncer de forma   ordenada", ctx)
    assert not jueces.cita_valida("Reinicia Redis de forma ordenada", ctx)
    assert not jueces.cita_valida("  ", ctx)


def test_cita_valida_ignora_el_formato_de_las_tablas() -> None:
    ctx = "| Servicio | Disponibilidad |\n| --- | --- |\n| pagos | 99,95 % |\n| busqueda | 99,5 % |"
    cita = "pagos | 99,95 % | busqueda | 99,5 %"
    assert not jueces.cita_literal(cita, ctx)
    assert jueces.cita_valida(cita, ctx)

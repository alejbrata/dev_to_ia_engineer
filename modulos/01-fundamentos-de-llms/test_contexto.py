import contexto


def test_prompt_coloca_el_dato_donde_toca() -> None:
    al_principio = contexto.construir_prompt(3, dato_al_final=False)
    al_final = contexto.construir_prompt(3, dato_al_final=True)

    assert al_principio.startswith(contexto.DATO)
    assert al_final.index(contexto.DATO) > al_final.index("Párrafo 3")
    assert al_principio.endswith(contexto.PREGUNTA) and al_final.endswith(contexto.PREGUNTA)


def test_recortado_si_el_servidor_procesa_menos_que_el_texto() -> None:
    assert contexto.recortado(tokens_texto=6000, tokens_procesados=2050)
    # Con la plantilla de chat, el servidor procesa más tokens que tu texto.
    assert not contexto.recortado(tokens_texto=6000, tokens_procesados=6029)

"""Prompts como código: catálogo, variables comprobadas y versión en las trazas.

1. Lista los prompts de `prompts/` con su versión y descripción.
2. Simula un cambio a medias: en el fichero del prompt la variable pasa a llamarse
   `{{texto}}`, pero el código sigue rellenando `ticket`. Con un reemplazo ingenuo, el
   modelo recibe `{{texto}}` tal cual. Con `curso_core.prompts`, falla antes de llamarlo.
3. Clasifica unos tickets con dos prompts y resume las trazas agrupadas por prompt.

Uso: `uv run python modulos/02-prompting/prompts_como_codigo.py`
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import tickets
from curso_core import ClienteLLM, Mensaje, Opciones, prompts
from curso_core.metrics import resumir_por
from curso_core.tracing import leer
from medir_prompts import empezar_de_cero

OPCIONES = Opciones(temperatura=0, max_tokens=200)


def catalogo() -> None:
    # Solo los de este módulo: en prompts/ hay también los de los módulos siguientes.
    print("1. Prompts de tickets del repositorio")
    carpeta = prompts.carpeta_por_defecto()
    for fichero in sorted((carpeta / "tickets").glob("*.md")):
        if fichero.name == "README.md":
            continue
        nombre = fichero.relative_to(carpeta).with_suffix("").as_posix()
        p = prompts.cargar(nombre)
        print(f"   {p.id:30} {p.descripcion}")


def cambio_a_medias(cliente: ClienteLLM, caso: tickets.Ticket) -> None:
    print("\n2. La variable se renombra en el prompt, pero no en el código")
    original = (prompts.carpeta_por_defecto() / "tickets" / "con-formato.md").read_text(
        encoding="utf-8"
    )
    renombrado = original.replace("{{ticket}}", "{{texto}}").replace(
        "variables: ticket", "variables: texto"
    )

    # a) Reemplazo ingenuo: busca {{ticket}}, no lo encuentra y no se queja.
    usuario = renombrado.split("## Usuario", 1)[1].strip()
    enviado = usuario.replace("{{ticket}}", caso.texto)
    r = cliente.chat([Mensaje(role="user", content=enviado)], opciones=OPCIONES)
    print(f"   a) reemplazo ingenuo. Lo que recibe el modelo termina en: {enviado[-25:]!r}")
    print(f"      y responde: {r.texto.strip()!r}")

    # b) curso_core.prompts: comprueba las variables antes de llamar al modelo.
    with TemporaryDirectory() as carpeta:
        (Path(carpeta) / "tickets").mkdir()
        (Path(carpeta) / "tickets" / "con-formato.md").write_text(renombrado, encoding="utf-8")
        prompt = prompts.cargar("tickets/con-formato", Path(carpeta))
        try:
            prompts.renderizar(prompt, ticket=caso.texto)
        except prompts.ErrorPrompt as e:
            print(f"   b) curso_core.prompts: ErrorPrompt: {e}")


def trazas_por_prompt(cliente: ClienteLLM, casos: list[tickets.Ticket]) -> None:
    print("\n3. Trazas agrupadas por prompt")
    with TemporaryDirectory() as carpeta:
        cliente.trazas = Path(carpeta) / "trazas.jsonl"
        for nombre in ["tickets/completo", "tickets/few-shot-5"]:
            empezar_de_cero(cliente)
            prompt = prompts.cargar(nombre)
            for caso in casos:
                cliente.chat(prompts.renderizar(prompt, ticket=caso.texto), opciones=OPCIONES)
        for clave, r in resumir_por(leer(cliente.trazas), "prompt").items():
            entrada = r.tokens_entrada // r.llamadas
            print(
                f"   {clave:24} {r.llamadas} llamadas · {entrada} tokens de entrada de media "
                f"· p50 {r.latencia_p50_s:.2f} s"
            )


def main() -> int:
    casos = tickets.cargar("eval")
    cliente = ClienteLLM()
    catalogo()
    cambio_a_medias(cliente, casos[0])
    trazas_por_prompt(cliente, casos[:5])
    return 0


if __name__ == "__main__":
    sys.exit(main())

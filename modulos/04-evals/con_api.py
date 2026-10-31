"""Opcional (anexo G): el sistema vigente con un modelo de API comercial en lugar del local.

Responde las mismas preguntas con la misma recuperación y el mismo prompt que evaluar.py;
solo cambia el rol del modelo que genera. Compara con resultados/vigente.jsonl caso a caso
y mide el coste y la latencia de las llamadas a la API con las trazas de curso_core.

Necesita el reranker de la lección 05 del módulo 3 en marcha y la clave del proveedor en
.env (para el rol por defecto, OPENAI_API_KEY). Con --grabadas no llama a nada.
Uso: `uv run python modulos/04-evals/con_api.py [--rol chat_openai] [--grabadas]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import dataset
import evaluar
import sistema
from curso_core import ClienteLLM, ErrorLLM
from curso_core.evals import (
    Informe,
    ResultadoCaso,
    comparar,
    intervalo_wilson,
    prueba_mcnemar,
)
from curso_core.metrics import resumir
from curso_core.tracing import leer
from sistema import corpus


def ejecutar(rol: str, casos: list[dataset.Caso]) -> Informe:
    cliente = ClienteLLM()
    indice = sistema.indice(cliente, reranker=evaluar.SISTEMA["reranker"])
    prompt, k = evaluar.SISTEMA["prompt"], evaluar.SISTEMA["k"]
    resultados = []
    with TemporaryDirectory() as carpeta:
        cliente.trazas = Path(carpeta) / "trazas.jsonl"
        for c in casos:
            r = sistema.responder(cliente, indice, c.pregunta, prompt=prompt, k=k, rol=rol)
            resultados.append(
                ResultadoCaso(
                    caso=c.id,
                    ok=dataset.puntuar(c, r.texto),
                    salida=r.texto,
                    detalle={"se_abstiene": corpus.se_abstiene(r.texto), "citas": r.citas},
                )
            )
        # Solo las llamadas del modelo que genera: fuera embeddings y reranker.
        trazas = [t for t in leer(cliente.trazas) if t.rol == rol]
    _, _, modelo = cliente.config.resolver(rol)
    meta = {"rol": rol, "modelo": modelo, "uso": resumir(trazas).model_dump()}
    return Informe(version=f"api-{rol}", resultados=resultados, meta=meta)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rol", default="chat_openai", help="rol de config/models.toml")
    parser.add_argument("--grabadas", action="store_true", help="no llama a ningún modelo")
    args = parser.parse_args()
    casos = dataset.cargar()
    por_id = {c.id: c for c in casos}
    ruta = evaluar.AQUI / "resultados" / f"api-{args.rol}.jsonl"

    if args.grabadas:
        api = Informe.cargar(ruta)
        for r in api.resultados:
            r.ok = dataset.puntuar(por_id[r.caso], r.salida)
    else:
        try:
            api = ejecutar(args.rol, casos)
        except ErrorLLM as e:
            print(f"No se puede usar el rol {args.rol}: {e}")
            return 1
        api.guardar(ruta)
    vigente = Informe.cargar(evaluar.VIGENTE)
    for r in vigente.resultados:
        r.ok = dataset.puntuar(por_id[r.caso], r.salida)

    print(f"1. Aciertos: modelo local frente a {api.meta['modelo']} (rol {args.rol})")
    for nombre, informe in [("local (vigente)", vigente), (api.meta["modelo"], api)]:
        con = [r for r in informe.resultados if por_id[r.caso].debe_responder]
        sin = [r for r in informe.resultados if not por_id[r.caso].debe_responder]
        bajo, alto = intervalo_wilson(informe.aciertos, informe.total)
        print(
            f"   {nombre:16} {informe.aciertos:2} de {informe.total} [{bajo:4.0%}, {alto:4.0%}]"
            f" · con respuesta {sum(r.ok for r in con):2} de {len(con)}"
            f" · no deben responderse {sum(r.ok for r in sin):2} de {len(sin)}"
        )
    c = comparar(vigente, api)
    p = prueba_mcnemar(len(c.ganados), len(c.perdidos))
    print(f"   la API gana {c.ganados}, pierde {c.perdidos}, p = {p:.2f}")

    uso = api.meta["uso"]
    print("\n2. Lo que cuesta la API (solo las llamadas que generan)")
    coste = uso["coste_usd"]
    print(
        f"   {uso['llamadas']} llamadas · {uso['errores']} errores · "
        f"{uso['tokens_entrada']} tokens de entrada · {uso['tokens_salida']} de salida"
    )
    print(
        f"   coste {coste:.4f} USD · {coste / uso['llamadas'] * 1000:.2f} USD por cada 1000 "
        f"preguntas · latencia p50 {uso['latencia_p50_s']:.2f} s, p95 {uso['latencia_p95_s']:.2f} s"
    )
    if uso["llamadas_sin_precio"]:
        print(f"   {uso['llamadas_sin_precio']} llamadas sin precio en models.toml")
    return 0


if __name__ == "__main__":
    sys.exit(main())

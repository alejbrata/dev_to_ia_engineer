"""Anexo C: Graph of Thoughts frente a una sola llamada, con el ejemplo del artículo.

Ordena listas de dígitos (con repetidos) de tres formas, con el mismo modelo:
1. Una llamada: la lista entera, ordenada de una vez.
2. Una llamada y corregir: lo mismo, y si el código encuentra errores, una llamada más
   con los problemas. Separa el efecto de corregir del de descomponer.
3. Graph of Thoughts: la lista en cuatro trozos que se ordenan por separado (generar),
   se mezclan de dos en dos (agregar) y, tras cada paso con errores, se corrigen una vez
   con la realimentación del código (refinar), quedándose con la mejor versión.

Los errores los cuenta el código: elementos que faltan o sobran frente a la original y
pares contiguos desordenados. Es la puntuación que usa el grafo para decidir si corrige.

Necesita Ollama con el modelo del rol (por defecto, chat_grande). Unos 50 minutos en la
CPU del curso; con --grabadas, un segundo.
Uso: `uv run python modulos/c-desarrollo-con-ia/graph_of_thoughts.py [--grabadas] [--rol ROL]`
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from curso_core import config as cfg
from pydantic import BaseModel

AQUI = Path(__file__).resolve().parent
RESULTADOS = cfg.carpeta_resultados(AQUI / "resultados")
TAMANOS = [32, 64]
LISTAS = 8
TROZOS = 4


class Lista(BaseModel):
    numeros: list[int]


def errores(original: list[int], propuesta: list[int]) -> int:
    """Elementos que faltan o sobran, más pares contiguos desordenados. 0 es perfecta."""
    a, b = Counter(original), Counter(propuesta)
    cuenta = sum(abs(a[d] - b[d]) for d in set(a) | set(b))
    desorden = sum(x > y for x, y in zip(propuesta, propuesta[1:], strict=False))
    return cuenta + desorden


def problemas(original: list[int], propuesta: list[int]) -> str:
    """La realimentación del código para el paso de refinar, en texto."""
    a, b = Counter(original), Counter(propuesta)
    faltan = [f"{d} (x{a[d] - b[d]})" for d in sorted(a) if a[d] > b[d]]
    sobran = [f"{d} (x{b[d] - a[d]})" for d in sorted(b) if b[d] > a[d]]
    pares = enumerate(zip(propuesta, propuesta[1:], strict=False))
    desorden = [f"{i + 1}-{i + 2}" for i, (x, y) in pares if x > y]
    partes = [
        f"faltan {', '.join(faltan)}" if faltan else "",
        f"sobran {', '.join(sobran)}" if sobran else "",
        f"desordenados en las posiciones {', '.join(desorden)}" if desorden else "",
    ]
    return "; ".join(p for p in partes if p)


@dataclass
class Gasto:
    llamadas: int = 0
    tokens: int = 0
    segundos: float = 0.0
    fallos_formato: int = 0
    pasos: list[str] = field(default_factory=list)


class Ordenador:
    def __init__(self, rol: str) -> None:
        from curso_core import ClienteLLM, Opciones, prompts

        self.cliente = ClienteLLM()
        self.rol = rol
        self.opciones = Opciones(temperatura=0, max_tokens=600)
        self.prompts = {
            n: prompts.cargar(f"razonamiento/{n}") for n in ("ordenar", "mezclar", "corregir")
        }
        self.renderizar = prompts.renderizar

    def llamar(self, nombre: str, gasto: Gasto, **valores: str) -> list[int]:
        from curso_core import ErrorFormato

        mensajes = self.renderizar(self.prompts[nombre], **valores)
        gasto.llamadas += 1
        try:
            lista, r = self.cliente.extraer(mensajes, Lista, rol=self.rol, opciones=self.opciones)
        except ErrorFormato as e:
            gasto.fallos_formato += 1
            if e.respuesta is not None:
                gasto.tokens += e.respuesta.tokens_entrada + e.respuesta.tokens_salida
                gasto.segundos += e.respuesta.latencia_s
            return []
        gasto.tokens += r.tokens_entrada + r.tokens_salida
        gasto.segundos += r.latencia_s
        return lista.numeros

    def refinar(self, original: list[int], propuesta: list[int], gasto: Gasto) -> list[int]:
        """Una corrección con la realimentación del código; se queda con la mejor."""
        if errores(original, propuesta) == 0:
            return propuesta
        corregida = self.llamar(
            "corregir",
            gasto,
            original=str(original),
            propuesta=str(propuesta),
            problemas=problemas(original, propuesta),
        )
        return min([propuesta, corregida], key=lambda p: errores(original, p))

    def una_llamada(self, lista: list[int], gasto: Gasto) -> list[int]:
        return self.llamar("ordenar", gasto, lista=str(lista))

    def una_y_corregir(self, lista: list[int], gasto: Gasto) -> list[int]:
        return self.refinar(lista, self.una_llamada(lista, gasto), gasto)

    def grafo(self, lista: list[int], gasto: Gasto) -> list[int]:
        n = len(lista) // TROZOS
        trozos = [lista[i * n : (i + 1) * n] for i in range(TROZOS)]
        # Generar: cada trozo, ordenado por separado (y refinado si el código ve errores).
        hojas = [
            (t, self.refinar(t, self.llamar("ordenar", gasto, lista=str(t)), gasto)) for t in trozos
        ]
        # Agregar: mezclar de dos en dos hasta una sola lista, refinando cada mezcla.
        while len(hojas) > 1:
            siguientes = []
            for (oa, a), (ob, b) in zip(hojas[::2], hojas[1::2], strict=True):
                original = oa + ob
                mezcla = self.llamar("mezclar", gasto, a=str(a), b=str(b))
                siguientes.append((original, self.refinar(original, mezcla, gasto)))
            hojas = siguientes
        return hojas[0][1]


METODOS = {
    "una llamada": "una_llamada",
    "una y corregir": "una_y_corregir",
    "graph of thoughts": "grafo",
}


def ejecutar(rol: str) -> dict:
    from curso_core import config as configuracion

    ordenador = Ordenador(rol)
    azar = random.Random(0)
    salida = {"modelo": configuracion.cargar().resolver(rol)[2], "rol": rol, "casos": []}
    for tamano in TAMANOS:
        for i in range(LISTAS):
            lista = [azar.randint(0, 9) for _ in range(tamano)]
            caso = {"tamano": tamano, "lista": lista, "metodos": {}}
            for nombre, metodo in METODOS.items():
                gasto = Gasto()
                propuesta = getattr(ordenador, metodo)(lista, gasto)
                caso["metodos"][nombre] = {
                    "propuesta": propuesta,
                    "errores": errores(lista, propuesta),
                    "llamadas": gasto.llamadas,
                    "tokens": gasto.tokens,
                    "segundos": gasto.segundos,
                    "fallos_formato": gasto.fallos_formato,
                }
            salida["casos"].append(caso)
            resumen = {m: caso["metodos"][m]["errores"] for m in METODOS}
            print(
                f"   {tamano} dígitos, lista {i + 1}: errores {resumen}",
                file=sys.stderr,
                flush=True,
            )
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grabadas", action="store_true", help="no llama al modelo")
    parser.add_argument("--rol", default="chat_grande", help="el modelo, como rol de models.toml")
    args = parser.parse_args()
    ruta = RESULTADOS / f"got-{args.rol}.json"
    if args.grabadas:
        r = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        r = ejecutar(args.rol)
        RESULTADOS.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"1. Ordenar {LISTAS} listas de dígitos de cada tamaño, con {r['modelo']}")
    print(
        f"   {'método':18} {'tamaño':>6} {'errores':>8} {'perfectas':>10} "
        f"{'llamadas':>9} {'tokens':>7} {'s/lista':>8}"
    )
    for tamano in TAMANOS:
        casos = [c for c in r["casos"] if c["tamano"] == tamano]
        for nombre in METODOS:
            m = [c["metodos"][nombre] for c in casos]
            n = len(m)
            media = {
                k: sum(x[k] for x in m) / n for k in ("errores", "llamadas", "tokens", "segundos")
            }
            print(
                f"   {nombre:18} {tamano:>6} {media['errores']:>8.1f} "
                f"{sum(x['errores'] == 0 for x in m):>6} de {n} "
                f"{media['llamadas']:>9.1f} {media['tokens']:>7.0f} {media['segundos']:>8.1f}"
            )
    print("   (errores, llamadas, tokens y segundos: media por lista)")

    fallos = sum(c["metodos"][m]["fallos_formato"] for c in r["casos"] for m in METODOS)
    print(f"\n2. Respuestas sin JSON válido: {fallos}")

    caso = next(
        (
            c
            for c in r["casos"]
            if c["tamano"] == TAMANOS[-1] and c["metodos"]["una llamada"]["errores"]
        ),
        r["casos"][-1],
    )
    print(f"\n3. Un caso de {caso['tamano']} dígitos")
    print(f"   original:          {''.join(map(str, caso['lista']))}")
    print(f"   correcta:          {''.join(map(str, sorted(caso['lista'])))}")
    for nombre in METODOS:
        m = caso["metodos"][nombre]
        print(f"   {nombre + ':':18} {''.join(map(str, m['propuesta']))}  ({m['errores']} errores)")
        detalle = problemas(caso["lista"], m["propuesta"])
        if detalle:
            print(f"      {detalle[:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

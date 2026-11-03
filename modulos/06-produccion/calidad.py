"""La calidad del asistente en producción, sin saber la respuesta correcta (lección 6.09).

De las cuatro métricas de RAG de la lección 4.05, tres se pueden calcular sin la respuesta
correcta, solo con la pregunta, los fragmentos y la respuesta:

- **Fidelidad**: el juez v2 del módulo 4 (el modelo cita, el código comprueba la cita).
- **Relevancia de la respuesta**: el juez de relevancia v2 de la lección 4.05 (cita y comprueba).
- **Precisión del contexto**: un juez que dice qué fragmentos sirven para la pregunta.

La cuarta, el recall del contexto, necesita saber qué fragmento tenía la respuesta: solo
se mide con la eval.

`EvaluadorEnLinea` juzga una muestra de las respuestas en segundo plano, sin retrasar la
respuesta al usuario, y publica las métricas por versión (lección 6.03).
"""

from __future__ import annotations

import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "04-evals"))

import jueces  # noqa: E402
from asistente import Resultado  # noqa: E402
from curso_core import ClienteLLM, ErrorFormato, prompts  # noqa: E402
from curso_core.rag import Fragmento  # noqa: E402
from curso_core.rag import Resultado as Recuperado  # noqa: E402
from sistema import corpus, generacion  # noqa: E402


class Utiles(BaseModel):
    motivo: str
    utiles: list[int]


def juzgar(
    cliente: ClienteLLM, pregunta: str, texto: str, fragmentos: list[Fragmento], rol: str = "judge"
) -> dict:
    """Las tres métricas de una respuesta. Fidelidad y relevancia, solo si no se abstiene:
    abstenerse "no responde", y en una pregunta sin respuesta es lo correcto."""
    ctx = generacion.contexto([Recuperado(fragmento=f, puntuacion=0.0) for f in fragmentos])
    abstiene = corpus.se_abstiene(texto)
    inicio = time.perf_counter()
    fiel = None if abstiene else jueces.juzgar_v2(cliente, pregunta, texto, ctx, rol=rol).fiel
    relevante = None if abstiene else jueces.relevancia_v2(cliente, pregunta, texto, rol=rol)
    mensajes = prompts.renderizar(
        prompts.cargar("rag/juez-precision"), contexto=ctx, pregunta=pregunta
    )
    try:
        elegidos = cliente.extraer(mensajes, Utiles, rol=rol, opciones=jueces.OPCIONES)[0].utiles
    except ErrorFormato:
        elegidos = []
    utiles = sorted({i for i in elegidos if 1 <= i <= len(fragmentos)})
    return {
        "abstiene": abstiene,
        "fiel": fiel,
        "relevante": relevante,
        "utiles": utiles,
        "precision": len(utiles) / len(fragmentos) if fragmentos else 0.0,
        "segundos": time.perf_counter() - inicio,
    }


class EvaluadorEnLinea:
    """Juzga una fracción de las respuestas en un hilo aparte, de una en una.

    Solo las que generó un modelo: las de la caché ya se juzgaron (o no) cuando se
    generaron, y la respuesta degradada o bloqueada no viene del modelo.
    """

    def __init__(
        self,
        cliente: ClienteLLM,
        fragmentos: dict[str, Fragmento],
        muestreo: float,
        semilla: int = 0,
        al_evaluar=None,
    ):
        self.cliente, self.fragmentos, self.muestreo = cliente, fragmentos, muestreo
        self._azar = random.Random(semilla)
        self._hilo = ThreadPoolExecutor(max_workers=1)
        self._al_evaluar = al_evaluar
        self.evaluadas: list[dict] = []
        self.descartadas = 0

    def enviar(self, pregunta: str, r: Resultado, version: str, **extra) -> bool:
        if r.cache or r.rol is None or r.bloqueado:
            return False
        if self._azar.random() >= self.muestreo:
            self.descartadas += 1
            return False
        self._hilo.submit(self._evaluar, pregunta, r, version, extra)
        return True

    def _evaluar(self, pregunta: str, r: Resultado, version: str, extra: dict) -> None:
        fragmentos = [self.fragmentos[i] for i in r.fuentes if i in self.fragmentos]
        juicio = juzgar(self.cliente, pregunta, r.texto, fragmentos)
        juicio |= {"version": version, "pregunta": pregunta, **extra}
        self.evaluadas.append(juicio)
        if self._al_evaluar:
            self._al_evaluar(version, juicio)

    def esperar(self) -> None:
        """Espera a que terminen las evaluaciones pendientes (al parar el servicio)."""
        self._hilo.shutdown(wait=True)


def resumen(evaluadas: list[dict]) -> dict:
    """Las tres métricas de un conjunto de evaluaciones, como en un panel."""
    contestan = [e for e in evaluadas if not e["abstiene"]]
    n = len(contestan)
    return {
        "evaluadas": len(evaluadas),
        "contestan": n,
        "fidelidad": sum(bool(e["fiel"]) for e in contestan) / n if n else None,
        "relevancia": sum(bool(e["relevante"]) for e in contestan) / n if n else None,
        "precision": sum(e["precision"] for e in evaluadas) / len(evaluadas) if evaluadas else None,
    }

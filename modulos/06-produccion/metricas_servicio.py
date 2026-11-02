"""Las métricas del asistente, en formato Prometheus (lección 6.03).

servicio.py las expone en GET /metrics. Dos niveles:

- Por pregunta: cuántas, con qué resultado (caché, principal, respaldo o degradada) y
  cuánto tardaron, en un histograma.
- Por llamada a un modelo: llamadas, tokens y coste, por rol. Llegan de curso_core a
  través de sus observadores de trazas, así que cubren también embeddings y reranker.

Las etiquetas son pocas y de valores fijos: cada combinación es una serie distinta en
Prometheus, y una etiqueta con valores libres (la pregunta, el usuario) lo saturaría.
"""

from __future__ import annotations

from asistente import Resultado
from curso_core.tracing import Traza
from prometheus_client import Counter, Histogram

# Cubetas para lo que tarda un LLM en CPU: desde la caché (milisegundos) hasta el timeout
# del principal (45 s) y lo que tarda el respaldo cuando el principal se cuelga.
CUBETAS = (0.005, 0.05, 0.25, 1, 2.5, 5, 7.5, 10, 12.5, 15, 20, 30, 45, 60, 90, 120)

PREGUNTAS = Counter(
    "asistente_preguntas_total", "Preguntas respondidas, por resultado", ["resultado"]
)
DURACION = Histogram(
    "asistente_duracion_segundos",
    "Lo que tarda en responder una pregunta, por resultado",
    ["resultado"],
    buckets=CUBETAS,
)
LLAMADAS = Counter(
    "llm_llamadas_total", "Llamadas a modelos, por rol y si fueron bien", ["rol", "ok"]
)
TOKENS = Counter("llm_tokens_total", "Tokens de las llamadas a modelos", ["rol", "tipo"])
COSTE = Counter("llm_coste_usd_total", "Coste de las llamadas a modelos, en dólares", ["rol"])


def resultado_de(r: Resultado) -> str:
    if r.bloqueado:
        return "bloqueada"
    if r.cache:
        return "cache"
    if r.rol is None:
        return "degradada"
    return "respaldo" if r.fallback else "principal"


def observar_pregunta(r: Resultado) -> None:
    resultado = resultado_de(r)
    PREGUNTAS.labels(resultado).inc()
    DURACION.labels(resultado).observe(r.ms / 1000)


def observar_llamada(t: Traza) -> None:
    """Observador de curso_core: se llama con cada traza de una llamada a un modelo."""
    LLAMADAS.labels(t.rol, str(t.ok).lower()).inc()
    TOKENS.labels(t.rol, "entrada").inc(t.tokens_entrada or 0)
    TOKENS.labels(t.rol, "salida").inc(t.tokens_salida or 0)
    COSTE.labels(t.rol).inc(t.coste_usd or 0.0)

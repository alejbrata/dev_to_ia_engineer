"""Trazas con OpenTelemetry para el asistente (lección 6.02).

`configurar()` instala el SDK de OpenTelemetry con dos destinos:

- Un fichero JSONL local (un span por línea), que basta para estudiar las trazas sin
  instalar nada. Por defecto, trazas/otel.jsonl; con OTEL_FICHERO, otro.
- Si está definida la variable estándar OTEL_EXPORTER_OTLP_ENDPOINT, además se envían por
  OTLP a cualquier backend compatible: Jaeger, Grafana Tempo, Langfuse, Honeycomb...

El código que crea los spans (curso_core, asistente.py, servicio.py) solo usa la API de
OpenTelemetry. Sin `configurar()`, esa API no hace nada y no cuesta casi nada: es la misma
separación que entre una fachada de logging y su implementación.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Sequence
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

FICHERO = Path("trazas") / "otel.jsonl"


class ExportadorJSONL(SpanExporter):
    """Escribe cada span como una línea JSON: id de traza, padre, nombre, tiempos, atributos."""

    def __init__(self, ruta: Path):
        self.ruta = ruta
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._bloqueo = threading.Lock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        lineas = []
        for s in spans:
            lineas.append(
                json.dumps(
                    {
                        "traza": format(s.context.trace_id, "032x"),
                        "span": format(s.context.span_id, "016x"),
                        "padre": format(s.parent.span_id, "016x") if s.parent else None,
                        "nombre": s.name,
                        "inicio_ns": s.start_time,
                        "fin_ns": s.end_time,
                        "ms": (s.end_time - s.start_time) / 1e6,
                        "estado": s.status.status_code.name,
                        "atributos": dict(s.attributes or {}),
                    },
                    ensure_ascii=False,
                )
            )
        with self._bloqueo, self.ruta.open("a", encoding="utf-8") as f:
            f.write("".join(linea + "\n" for linea in lineas))
        return SpanExportResult.SUCCESS


def configurar(servicio: str = "asistente-documentacion") -> TracerProvider:
    proveedor = TracerProvider(resource=Resource.create({"service.name": servicio}))
    ruta = Path(os.environ.get("OTEL_FICHERO", FICHERO))
    proveedor.add_span_processor(BatchSpanProcessor(ExportadorJSONL(ruta)))
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        proveedor.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(proveedor)
    return proveedor


def leer(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]

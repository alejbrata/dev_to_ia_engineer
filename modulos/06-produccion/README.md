# Módulo 6 — Producción: código de las prácticas

El caso del módulo es el sistema vigente del módulo 4 (el RAG con reranker que se evaluó)
convertido en un servicio: el asistente de documentación interna.

- `asistente.py`: el sistema vigente con caché, fallback al modelo pequeño y respuesta degradada. No sabe nada de HTTP.
- `servicio.py`: la API con FastAPI (`POST /preguntas`, `POST /trabajos`, `GET /trabajos/{id}`, `GET /salud`). Arranque: `uv run uvicorn servicio:app --app-dir modulos/06-produccion --port 8100`.
- `arquitectura.py`: mide la caché, la concurrencia, la cola y el fallback contra el servicio en marcha, y la calidad del respaldo con la eval del módulo 4 (lección 01).
- `observabilidad.py`: configura OpenTelemetry (un fichero JSONL y, con `OTEL_EXPORTER_OTLP_ENDPOINT`, OTLP). El servicio lo usa con `ASISTENTE_TRAZAS=1`.
- `observar.py`: lee las trazas del servicio (cascada, dónde se va el tiempo, coste de trazar); con `--jaeger`, también en Jaeger (lección 02).
- `test_produccion.py`: la caché y la API con un asistente falso, sin modelos.
- `resultados/`: lo que midió cada práctica. Con `--grabadas`, se reutiliza sin llamar a nada.

Las prácticas necesitan Ollama con los modelos del módulo 4 y el reranker de la lección 3.05 en marcha.

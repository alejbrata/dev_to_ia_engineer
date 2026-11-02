# Módulo 6 — Producción: código de las prácticas

El caso del módulo es el sistema vigente del módulo 4 (el RAG con reranker que se evaluó)
convertido en un servicio: el asistente de documentación interna.

- `asistente.py`: el sistema vigente con caché, fallback al modelo pequeño y respuesta degradada. No sabe nada de HTTP.
- `servicio.py`: la API con FastAPI (`POST /preguntas`, `POST /trabajos`, `GET /trabajos/{id}`, `GET /salud`). Arranque: `uv run uvicorn servicio:app --app-dir modulos/06-produccion --port 8100`.
- `arquitectura.py`: mide la caché, la concurrencia, la cola y el fallback contra el servicio en marcha, y la calidad del respaldo con la eval del módulo 4 (lección 01).
- `observabilidad.py`: configura OpenTelemetry (un fichero JSONL y, con `OTEL_EXPORTER_OTLP_ENDPOINT`, OTLP). El servicio lo usa con `ASISTENTE_TRAZAS=1`.
- `observar.py`: lee las trazas del servicio (cascada, dónde se va el tiempo, coste de trazar); con `--jaeger`, también en Jaeger (lección 02).
- `metricas_servicio.py`: las métricas de Prometheus que el servicio expone en `GET /metrics` (preguntas por resultado, histograma de duración, llamadas, tokens y coste por rol).
- `metricas_operativas.py`: tráfico normal y un pico, leídos de `/metrics`; p50/p95, tasas de caché y respaldo, coste por pregunta y SLO (lección 03).
- `privacidad.py`: detecta y redacta datos personales (email, teléfono, DNI, NIE, IBAN, tarjeta) y secretos con expresiones regulares.
- `amenazas.py`: inyección directa e indirecta (una página del runbook editada), datos personales y una clave en el historial de git, limpiada con `git filter-repo` (lección 04).
- `guardrails.py`: comprobaciones de entrada (inyección, datos personales) y de salida (sin fundamento, contacto externo, credenciales, comandos destructivos). El asistente las aplica con `guardrails=True`; el servicio, con `ASISTENTE_GUARDRAILS=1`.
- `defensas.py`: los guardrails con las 58 respuestas del módulo 4 (falsos positivos) y con nueve ataques en vivo (lección 05).
- `Dockerfile` y `compose.yaml`: la imagen del servicio (dos etapas, uv, usuario sin privilegios, healthcheck) y su arranque. Construcción desde la raíz: `docker build -f modulos/06-produccion/Dockerfile -t asistente .`. El `.dockerignore` está en la raíz.
- `desplegar.py`: construir, inspeccionar, arrancar y parar el contenedor, medido (lección 06).
- `incidentes.py`: dos incidentes provocados (el reranker caído y el modelo cambiado con `CURSO_ROLES`) leídos con `/salud`, métricas, trazas y calidad (lección 07).
- `test_produccion.py`: la caché y la API con un asistente falso, sin modelos.
- `resultados/`: lo que midió cada práctica. Con `--grabadas`, se reutiliza sin llamar a nada.

Las prácticas necesitan Ollama con los modelos del módulo 4 y el reranker de la lección 3.05 en marcha.

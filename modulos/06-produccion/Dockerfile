# La imagen del asistente de documentación (lección 6.06).
# Se construye desde la raíz del repo, porque necesita curso_core, el corpus y el sistema
# del módulo 4:
#   docker build -f modulos/06-produccion/Dockerfile -t asistente .
# Los modelos no van dentro: Ollama y el reranker se usan por red (CURSO_URL_*).

# Etapa 1: las dependencias, con uv. Solo lo que hace falta para instalarlas, para que
# Docker reutilice esta capa mientras no cambien pyproject.toml ni uv.lock.
FROM python:3.12-slim-bookworm AS dependencias
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages ./packages
# Sin el grupo de desarrollo ni el opcional hf (torch): solo lo que usa el servicio.
RUN uv sync --frozen --no-dev

# Etapa 2: lo que se ejecuta. Sin uv, sin compiladores y con un usuario sin privilegios.
FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 1000 asistente
WORKDIR /app
COPY --from=dependencias /app/.venv ./.venv
COPY --from=dependencias /app/packages ./packages
COPY config ./config
COPY prompts ./prompts
COPY modulos/03-rag ./modulos/03-rag
COPY modulos/04-evals ./modulos/04-evals
COPY modulos/06-produccion ./modulos/06-produccion
# Las trazas de curso_core, en un sitio donde el usuario puede escribir.
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 CURSO_TRAZAS=/tmp/trazas/llamadas.jsonl
USER asistente
EXPOSE 8100
HEALTHCHECK --interval=10s --timeout=3s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/salud')"
# uvicorn atiende SIGTERM: `docker stop` le deja cerrar con orden (lección 6.02).
CMD ["uvicorn", "servicio:app", "--app-dir", "modulos/06-produccion", "--host", "0.0.0.0", "--port", "8100"]

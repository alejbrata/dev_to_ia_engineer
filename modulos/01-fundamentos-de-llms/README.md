# Módulo 1 — Fundamentos de LLMs: código de las prácticas

- `tokens.py`: trocea textos con el tokenizador real del modelo y compara tokens.
- `prediccion.py`: muestra la probabilidad de cada token generado y sus alternativas.
- `contexto.py`: qué pasa cuando el prompt no cabe en la ventana de contexto (solo Ollama).
- `sampling.py`: temperatura, top_p y semilla, medidos sobre el modelo.
- `tres_formas.py`: la misma llamada con HTTP a mano, el SDK de OpenAI y curso_core.
- `conversacion.py`: mensajes, roles y por qué hay que reenviar el historial.
- `streaming.py`: streaming y tiempo hasta el primer fragmento.
- `errores_api.py`: errores reales de Hugging Face Inference Providers (401, 400, 402) y un timeout.

Ejecútalos desde la raíz del repo con `uv run python modulos/01-fundamentos-de-llms/<script>.py`.

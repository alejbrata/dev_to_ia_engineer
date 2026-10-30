# Módulo 1 — Fundamentos de LLMs: código de las prácticas

- `tokens.py`: trocea textos con el tokenizador real del modelo y compara tokens.
- `prediccion.py`: muestra la probabilidad de cada token generado y sus alternativas.
- `contexto.py`: qué pasa cuando el prompt no cabe en la ventana de contexto (solo Ollama).
- `contexto_llamacpp.py`: el mismo prompt contra llama-server, que rechaza en vez de recortar.
- `sampling.py`: temperatura, top_p y semilla, medidos sobre el modelo.
- `tres_formas.py`: la misma llamada con HTTP a mano, el SDK de OpenAI y curso_core.
- `conversacion.py`: mensajes, roles y por qué hay que reenviar el historial.
- `streaming.py`: streaming y tiempo hasta el primer fragmento.
- `errores_api.py`: errores reales de Hugging Face Inference Providers (401, 400, 402) y un timeout.
- `ficha_modelo.py`: ficha de un modelo en el Hub de Hugging Face (licencia, tamaño, modelo base).
- `comparar_modelos.py`: tres tamaños de la misma familia con las mismas preguntas.
- `coste_y_latencia.py`: p50/p95 de una carga real y proyección de coste.
- `reintentos.py` y `simulador.py`: reintentos frente a un límite de uso (429) simulado.

Ejecútalos desde la raíz del repo con `uv run python modulos/01-fundamentos-de-llms/<script>.py`.

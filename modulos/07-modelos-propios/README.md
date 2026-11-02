# Módulo 7 — Modelos propios: código de las prácticas

El hilo del módulo: el asistente del módulo 6 con un modelo pequeño y abierto en lugar del
de 7B. ¿Se puede conseguir que se comporte como el grande en esta tarea, y a qué coste?

- `decidir.py`: lo que saben los modelos sin documentación y dónde falla el de 1,5B con RAG, con el dataset del módulo 4 (lección 01).
- `preparar.py`: descarga el modelo de 1,5B del Hub fijando el commit, calcula su memoria, muestra la plantilla de chat y lo compara cargado con transformers (con y sin plantilla) frente a Ollama (lección 02). Necesita `uv sync --group hf`.
- `servir.py` y `servidores.py`: el mismo modelo con Ollama, llama.cpp y vLLM (en Docker), una petición cada vez y cuatro a la vez, y la memoria que reserva cada servidor (lección 03).
- `cuantizar.py`: cuantiza el GGUF de 16 bits a seis niveles con `llama-quantize` y mide cada uno: velocidad, perplejidad y la eval del módulo 4 (lección 04).
- `test_modelos_propios.py`: la lógica que no necesita modelos ni red.
- `resultados/`: lo que midió cada práctica. Con `--grabadas`, se reutiliza sin llamar a nada.

Las lecciones 03 y 04 necesitan llama.cpp en el PATH o en `LLAMA_CPP_DIR` (ver `.env.example`).

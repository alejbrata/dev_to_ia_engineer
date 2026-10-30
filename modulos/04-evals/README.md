# Módulo 4 — Evals: código de las prácticas

Se evalúa el RAG del módulo 3. `sistema.py` lo envuelve (búsqueda densa, opcionalmente con reranker, k fragmentos y prompt con citas); las prácticas lo llaman a través de él.

- `datos/casos.jsonl`: el dataset de referencia, 58 casos anclados a segmentos literales del corpus, con tipo, etiquetas y partición (desarrollo o prueba).
- `datos/casos_sin_anclar.jsonl`: 10 preguntas escritas a propósito sin mirar el corpus, para ver qué pasa.
- `datos/juez_etiquetas.jsonl`: 64 respuestas (46 reales y 18 alteradas) etiquetadas como fieles o no, con el segmento que las apoya o la afirmación sin apoyo.
- `dataset.py`: carga, validación del anclaje y puntuación por tipo (invertida en los que no deben responderse). `test_dataset.py` comprueba el anclaje en cada cambio.
- `parece_que_funciona.py`: el mismo cambio de prompt, probado a mano con 3 preguntas y medido con las 30 (lección 01).
- `datasets.py`: el mismo RAG evaluado con el dataset anclado y con el sin anclar (lección 02).
- `metricas.py`: comprobadores deterministas, intervalos de confianza y comparación de versiones, sobre los resultados grabados y sin modelo (lección 03).
- `jueces.py` y `calibrar_juez.py`: dos jueces de fidelidad calibrados contra las etiquetas (lección 04). `test_jueces.py` comprueba que las etiquetas están ancladas.
- `por_etapas.py`: tres configuraciones del sistema medidas por etapas (recuperación y generación), con la fidelidad según el juez v2 (lección 05). Necesita el reranker en `llama-server`.
- `resultados/`: resultados grabados caso a caso (`curso_core.evals.Informe`). Con `--grabadas`, las prácticas los reutilizan sin llamar al modelo.

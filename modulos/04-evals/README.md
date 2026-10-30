# Módulo 4 — Evals: código de las prácticas

Se evalúa el RAG del módulo 3. `sistema.py` lo envuelve (búsqueda densa, 3 fragmentos, prompt con citas); las prácticas lo llaman a través de él.

- `datos/casos.jsonl`: el dataset de referencia, 58 casos anclados a segmentos literales del corpus, con tipo, etiquetas y partición (desarrollo o prueba).
- `datos/casos_sin_anclar.jsonl`: 10 preguntas escritas a propósito sin mirar el corpus, para ver qué pasa.
- `dataset.py`: carga, validación del anclaje y puntuación por tipo (invertida en los que no deben responderse). `test_dataset.py` comprueba el anclaje en cada cambio.
- `parece_que_funciona.py`: el mismo cambio de prompt, probado a mano con 3 preguntas y medido con las 30 (lección 01).
- `datasets.py`: el mismo RAG evaluado con el dataset anclado y con el sin anclar (lección 02).
- `resultados/`: resultados grabados caso a caso (`curso_core.evals.Informe`). Con `--grabadas`, las prácticas los reutilizan sin llamar al modelo.

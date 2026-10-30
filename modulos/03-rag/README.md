# Módulo 3 — RAG: código de las prácticas

El caso del módulo: la documentación interna (inventada) de la plataforma de los tickets.

- `datos/docs/`: 29 documentos de arquitectura, runbooks, SLA, guardias y postmortems.
- `datos/preguntas.jsonl`: 30 preguntas (26 con respuesta, 4 sin ella), con evidencias y dato clave.
- `corpus.py`: carga, relevancia de un fragmento, abstención y corrección de una respuesta.
- `cuando_rag.py`: sin documentación, todo en el prompt o RAG.
- `chunking.py`: cuatro formas de trocear, con evidencias partidas, recall@3 y MRR.
- `embeddings.py`: tres configuraciones de embeddings y qué pasa si cambias de modelo sin reindexar.
- `indice_pgvector.py`: el mismo índice en PostgreSQL con pgvector. Necesita `docker compose up -d`.
- `recuperacion.py`: búsqueda densa, léxica (BM25) e híbrida (RRF), con preguntas e identificadores.
- `reranking.py`: reordenar candidatos con un cross-encoder. Necesita el reranker en `llama-server` (rol `reranker`).
- `generacion.py`: respuestas con citas, abstención, y fidelidad y relevancia medidas con un juez (rol `judge`).

Los prompts están en `prompts/rag/`, en la raíz del repo.

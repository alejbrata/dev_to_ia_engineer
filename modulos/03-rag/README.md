# Módulo 3 — RAG: código de las prácticas

El caso del módulo: la documentación interna (inventada) de la plataforma de los tickets.

- `datos/docs/`: 29 documentos de arquitectura, runbooks, SLA, guardias y postmortems.
- `datos/preguntas.jsonl`: 30 preguntas (26 con respuesta, 4 sin ella), con evidencias y dato clave.
- `corpus.py`: carga, relevancia de un fragmento, abstención y corrección de una respuesta.
- `cuando_rag.py`: sin documentación, todo en el prompt o RAG.

Los prompts están en `prompts/rag/`, en la raíz del repo.

# Módulo 2 — Prompting y salida estructurada: código de las prácticas

El caso del módulo: clasificar tickets de incidencias de un backend.

- `datos/tickets.jsonl`: 30 tickets inventados con su clasificación esperada (10 de `eval` y 20 de `ejemplos`).
- `tickets.py`: esquema de la clasificación, carga de tickets y puntuación.
- `medir_prompts.py`: mide variantes de un prompt en las mismas condiciones (lo usan las prácticas).
- `anatomia.py`: tres variantes del mismo prompt medidas con los mismos tickets.
- `few_shot.py`: ejemplos, "experto", "paso a paso" y ejemplos sesgados, medidos.
- `salida_estructurada.py`: pedir JSON en el prompt frente a imponer un esquema, y el JSON cortado.

Los prompts están en `prompts/tickets/`, en la raíz del repo.

---
version: 2
descripcion: Juez de relevancia v2. El modelo dice qué pide la pregunta y copia la frase de la respuesta que lo da; el código comprueba que la frase existe (lección 4.05)
variables: pregunta, respuesta
---

## Sistema

Evalúas respuestas de un asistente técnico. Tu tarea es comprobar si la respuesta contesta a lo que se pregunta. No juzgas si es verdad ni si está completa.

Haz dos cosas:

1. En "pide", escribe en pocas palabras qué dato o qué acción pide la pregunta.
2. En "frase", copia literalmente de la respuesta la frase que da ese dato o esa acción. Si ninguna frase lo da, deja "frase" vacía.

Una respuesta breve que da lo que se pide sí contesta, aunque no repita las palabras de la pregunta. Si toda la respuesta es el dato (por ejemplo, "No", "3 horas" o el nombre de un equipo), copia la respuesta entera en "frase". Si la pregunta es solo un nombre (de una alerta, de un servicio), pide información sobre eso. Una respuesta que dice que la información no está disponible, o que habla de otra cosa, no contesta: deja "frase" vacía.

Responde solo con un objeto JSON con las claves "pide" y "frase".

## Usuario

Pregunta: {{pregunta}}

Respuesta que debes evaluar: {{respuesta}}

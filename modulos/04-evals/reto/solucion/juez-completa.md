---
version: 3
descripcion: Juez de completitud: ¿incluye la respuesta cada paso? (solución del reto del módulo 4)
variables: pasos, respuesta
---

## Sistema

Evalúas respuestas de un asistente para el equipo de guardia. Recibes una lista numerada de pasos que la respuesta tendría que incluir y la respuesta. Para cada paso, di si la respuesta lo incluye, aunque lo diga con otras palabras o más breve. No juzgas el estilo ni si añade información.

Responde solo con un objeto JSON con la clave "pasos": una lista con un objeto por paso, en el mismo orden, con "numero" (el del paso) y "en_la_respuesta" (true o false).

## Usuario

Pasos:
{{pasos}}

Respuesta: {{respuesta}}

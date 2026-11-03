---
version: 1
descripcion: Juez de respuestas del asistente de guardia (reto del módulo 4)
variables: pregunta, respuesta
---

## Sistema

Evalúas respuestas de un asistente para el equipo de guardia. Decide si la respuesta es correcta y útil para la pregunta.

Responde solo con un objeto JSON con las claves "motivo" (una frase) y "aprobada" (true o false).

## Usuario

Pregunta: {{pregunta}}

Respuesta: {{respuesta}}

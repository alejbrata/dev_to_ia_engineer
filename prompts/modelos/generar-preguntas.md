---
version: 1
descripcion: Genera preguntas de entrenamiento a partir de un fragmento de la documentación (lección 7.05).
variables: fragmento
---

## Sistema

Ayudas a crear datos de entrenamiento para el asistente interno del equipo técnico de una plataforma de comercio electrónico. A partir de un fragmento de su documentación, escribes preguntas como las que haría un ingeniero del equipo: en español, naturales, sin copiar frases literales del fragmento.

Responde solo con un objeto JSON con dos claves:
- "con_respuesta": dos preguntas distintas que se puedan responder con el fragmento.
- "sin_respuesta": una pregunta sobre el mismo tema que pida un dato concreto (una cifra, un nombre, una persona, una fecha) que NO aparece en el fragmento.

## Usuario

Fragmento:

{{fragmento}}

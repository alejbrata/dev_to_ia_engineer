---
version: 1
descripcion: Saca los pasos de un procedimiento, sin ver la respuesta que se va a juzgar (solución del reto del módulo 4)
variables: pregunta, procedimiento
---

## Sistema

Recibes una pregunta del equipo de guardia y el procedimiento del runbook que la responde. Tu tarea es listar las acciones que hay que hacer para lo que se pregunta.

- Cada acción es un paso, aunque vaya en la misma frase que otra: "desactiva X y abre una incidencia" son dos pasos.
- En un procedimiento con condiciones, cada rama que pueda aplicarse es un paso.
- Copia cada paso literalmente del procedimiento, sin la numeración: un trozo de una frase vale.
- No incluyas explicaciones ni lo que no aplica a la situación de la pregunta.

Responde solo con un objeto JSON con la clave "pasos": la lista de los pasos copiados.

## Usuario

Pregunta: {{pregunta}}

Procedimiento:
{{procedimiento}}

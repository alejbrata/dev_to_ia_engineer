---
title: "Prompts como código"
description: "Prompts como código: versionado y plantillas"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el modelo con el que se construyó el curso (Qwen2.5 1.5B Instruct en Ollama). El formato de los ficheros de prompt es el de este curso; las ideas valen para cualquier formato.
:::

## Objetivos

Al terminar esta lección podrás:

- Explicar por qué un prompt es parte del comportamiento del sistema y se gestiona como código.
- Guardar prompts en ficheros versionados, con variables declaradas y comprobadas.
- Saber qué versión de qué prompt produjo cada respuesta, mirando las trazas.
- Detectar un prompt mal rellenado antes de que llegue al modelo.

## Teoría

### Un prompt es código

Cambiar una línea de un prompt cambia el comportamiento del sistema tanto como cambiar una línea de código: en la lección 01, quitar los criterios de severidad cambió los resultados de diez tickets. Y sin embargo, es habitual encontrar prompts como cadenas de texto enterradas en el código, editadas sin revisión y sin forma de saber cuál estaba en producción cuando algo salió mal.

Tratar los prompts como código significa aplicarles lo mismo que a cualquier artefacto que afecta a producción:

- **En el repositorio**, junto al código que los usa.
- **Versionados**, para saber qué versión produjo qué respuesta.
- **Revisados**, con sus cambios visibles en un diff de git.
- **Probados**, con una evaluación antes de cada cambio (lección 06).

Si vienes de backend, piensa en las migraciones de base de datos o en las plantillas de email: viven en ficheros propios, tienen versión y nadie las cambia en caliente en producción.

### Cómo los guarda este curso

Cada prompt es un fichero Markdown en `prompts/`, con una cabecera y secciones:

```markdown
---
version: 1
descripcion: El prompt completo más 5 ejemplos que cubren las cuatro severidades.
variables: ticket
---

## Sistema
...

## Ejemplos
### Usuario
...
### Asistente
...

## Usuario
Ticket:
{{ticket}}
```

Separarlos del código tiene ventajas prácticas: se leen como texto, cualquiera del equipo puede proponer un cambio sin tocar Python, y un diff muestra exactamente qué frase cambió. El formato completo está en [`prompts/README.md`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/README.md).

### Versión y trazas

El campo `version` existe para las trazas. Cuando pasas a `curso_core` un prompt renderizado, cada llamada queda registrada con su identificador:

```json
{"rol": "chat", "modelo": "qwen2.5:1.5b", "prompt": "tickets/few-shot-5@v1", ...}
```

Si una respuesta rara aparece en producción, sabes qué prompt la generó. Y si comparas métricas de dos versiones, sabes de cuál es cada una. La regla es sencilla: **cada cambio del prompt sube la versión**. Git conserva el historial completo; la versión lo hace visible en tiempo de ejecución.

### Variables comprobadas

Una plantilla tiene huecos (`{{ticket}}`) que el código rellena. Es un contrato entre el fichero y el código, y como todo contrato puede romperse: alguien renombra la variable en un lado y no en el otro. `curso_core.prompts` comprueba tres cosas antes de mandar nada al modelo:

- Que se rellenan todas las variables declaradas.
- Que no se pasan variables que el prompt no declara.
- Que el texto no usa variables sin declarar.

Si algo no cuadra, lanza `ErrorPrompt` y la llamada no se hace.

## Práctica

[`prompts_como_codigo.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/prompts_como_codigo.py) tiene tres partes:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/02-prompting/prompts_como_codigo.py
```

Primero, un catálogo de los prompts del repositorio, leído de sus cabeceras:

```text
1. Prompts de tickets del repositorio
   tickets/completo@v1            Rol, contexto, criterios de cada valor y formato. La base del resto del módulo.
   tickets/con-formato@v1         Pide un formato de respuesta y da los valores posibles, sin explicar qué significan.
   tickets/con-herramienta@v1     El prompt completo con una herramienta para consultar el estado del servicio...
   ...
   tickets/few-shot-5@v1          El prompt completo más 5 ejemplos que cubren las cuatro severidades...
   ...
```

Después, un cambio a medias: en el fichero del prompt, la variable pasa a llamarse `{{texto}}`, pero el código sigue rellenando `ticket`.

```text
2. La variable se renombra en el prompt, pero no en el código
   a) reemplazo ingenuo. Lo que recibe el modelo termina en: 'queda>\n\nTicket:\n{{texto}}'
      y responde: 'categoria: red\nseveridad: media\nservicio: usuarios'
   b) curso_core.prompts: ErrorPrompt: tickets/con-formato@v1: faltan variables ['texto'], sobran ['ticket']
```

Por último, unos tickets clasificados con dos prompts, y las trazas resumidas por prompt:

```text
3. Trazas agrupadas por prompt
   tickets/completo@v1      5 llamadas · 343 tokens de entrada de media · p50 0.71 s
   tickets/few-shot-5@v1    5 llamadas · 643 tokens de entrada de media · p50 0.79 s
```

Para ver la historia de un prompt, como la de cualquier fichero:

```sh title="Terminal de VS Code · raíz del repo"
git log -p -- prompts/tickets/few-shot-5.md
```

## Mide y depura

### Métricas por versión

La tercera parte de la práctica es la base para comparar versiones en producción: agrupar las trazas por `prompt` te da tokens, latencia, coste y errores de cada versión por separado. Si despliegas la versión 2 de un prompt y la tasa de error sube, lo ves en el resumen de esa versión, sin mezclarlo con la anterior.

Fíjate también en el coste: los cinco ejemplos de `few-shot-5` casi duplican los tokens de entrada (643 frente a 343). Cada versión tiene un precio, y las trazas lo muestran.

### El prompt que se manda de verdad

Cuando una respuesta no tiene sentido, lo primero es ver el prompt exactamente como lo recibió el modelo, con las variables ya rellenas. Pon un punto de ruptura en la llamada (lección 05 del módulo 0) e inspecciona los mensajes. Si un prompt sale de una plantilla, el error puede estar en la plantilla, en los datos o en cómo se rellenan.

## Errores frecuentes

**Prompts dentro del código.** Cadenas largas mezcladas con lógica, difíciles de revisar y duplicadas en varios sitios. Sácalos a ficheros.

**Cambiar el prompt sin subir la versión.** Las trazas dirán que la respuesta es de la versión 1 cuando en realidad es de un prompt distinto. Una versión que no cambia con el contenido es peor que no tener versión.

**Cambiar varias cosas a la vez.** Si en una misma versión añades ejemplos y cambias los criterios, no sabrás cuál de los dos cambios explica el resultado. Un cambio, una versión, una medición.

**Rellenar plantillas a mano.** Un `replace` que no encuentra lo que busca no da ningún error. Lo ves en la anatomía.

### Anatomía de un error: el ticket que no existía

Con el reemplazo ingenuo, el código busca `{{ticket}}` en el prompt, no lo encuentra (ahora se llama `{{texto}}`) y no hace nada. El modelo recibe esto:

```text
Ticket:
{{texto}}
```

Y responde, con total seguridad:

```text
categoria: red
severidad: media
servicio: usuarios
```

**Cómo leerlo.** No hay ningún error: ni excepción, ni código HTTP, ni respuesta inválida. La respuesta tiene el formato correcto y valores válidos. Solo la delata que no se corresponde con el ticket que querías clasificar. Si no comparas con el resultado esperado (lección 06), este fallo pasa a producción.

**Causa.** `str.replace` no avisa cuando no encuentra el texto que busca. El modelo, por su parte, no dice "no veo ningún ticket": hace lo que se le pide con lo que tiene. Un modelo rara vez se niega a contestar porque la entrada esté vacía o rota.

**Solución.** Declara las variables y comprueba que encajan antes de llamar al modelo. `curso_core.prompts` lo hace y lanza `ErrorPrompt` con las que faltan y las que sobran. Además, el repositorio tiene un test que carga todos los prompts de `prompts/` en cada ejecución de CI: un prompt mal formado no llega a `main`.

## Para profundizar

- [`prompts/README.md`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/README.md): el formato de los prompts del curso.
- [Plantillas de chat](https://huggingface.co/docs/transformers/chat_templating) en Hugging Face: otra capa de plantillas, la que convierte los mensajes en tokens (lección 01 del módulo 1).
- [Jinja](https://jinja.palletsprojects.com/): el motor de plantillas más usado en Python, por si tus prompts necesitan condicionales o bucles.

---
title: "Anatomía de un prompt"
description: "Anatomía de un prompt: system, instrucciones, contexto, ejemplos"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el modelo con el que se construyó el curso (Qwen2.5 1.5B Instruct en Ollama), temperatura 0. Con otro modelo, las cifras cambian; el método para medirlas, no.
:::

## Objetivos

Al terminar esta lección podrás:

- Identificar las partes de un prompt (mensaje de sistema, instrucciones, contexto, formato y datos) y para qué sirve cada una.
- Escribir un prompt con un formato de salida que tu código pueda leer.
- Medir un prompt con dos números distintos: cuántas respuestas son utilizables y cuántas aciertan.
- Explicar con datos por qué un prompt más largo no es necesariamente mejor.

## Teoría

### El caso de este módulo

Todo el módulo trabaja sobre la misma tarea: **clasificar tickets de incidencias** de una plataforma de comercio electrónico con cinco servicios (pagos, usuarios, catálogo, notificaciones y búsqueda). Cada ticket es un texto libre, como lo escribiría alguien del equipo:

```text
Desde las 9:40 el servicio de pagos devuelve 500 en todas las peticiones. En los logs sale
'too many connections' contra Postgres. Nadie puede pagar.
```

Y la clasificación que quieres obtener tiene tres campos:

```text
categoria: base_de_datos
severidad: critica
servicio: pagos
```

En `modulos/02-prompting/datos/tickets.jsonl` hay 30 tickets inventados para el curso, cada uno con su clasificación esperada. Diez están reservados para medir (el grupo `eval`) y veinte para sacar ejemplos en la lección siguiente (`ejemplos`). Separarlos evita medir con los mismos casos que le enseñas al modelo.

### Las partes de un prompt

Un prompt no es una frase: es una petición con varias piezas, y cada una tiene un trabajo.

| Parte | Qué hace | Dónde va |
| --- | --- | --- |
| **Rol y contexto** | Quién es el modelo en esta tarea y en qué entorno trabaja | Mensaje de sistema |
| **Instrucciones** | Qué tiene que hacer exactamente | Sistema o usuario |
| **Criterios** | Cómo decidir: qué significa cada valor posible | Mensaje de sistema |
| **Formato de salida** | Cómo tiene que responder, para que tu código lo lea | Mensaje de sistema |
| **Ejemplos** | Casos resueltos que muestran lo que esperas (lección 02) | Pares de mensajes |
| **Datos** | La entrada concreta de esta llamada: el ticket | Mensaje de usuario, al final |

Si vienes de backend, piensa en el prompt como en el contrato de una API que llama a un servicio que no controlas. Cuanto más ambiguo sea el contrato, más interpretaciones distintas recibirás. Y como en un contrato, lo que no especificas lo decide la otra parte.

Dos reglas de orden que se repiten en todo el curso:

- **Lo fijo, primero; lo variable, al final.** Las instrucciones son iguales en todas las llamadas y el ticket cambia. Ese orden ayuda a la caché del prompt (lección 06 del módulo 1).
- **Delimita los datos.** `Ticket:` seguido del texto deja claro dónde empiezan las instrucciones y dónde los datos.

### Más no siempre es mejor

La intuición dice que un prompt más detallado da mejores resultados. A veces sí. Pero cada línea que añades es algo más que el modelo tiene que tener en cuenta, y un modelo pequeño se pierde antes. La única forma de saber si una parte del prompt ayuda es quitarla y medir. Es lo que hace la práctica.

### Los prompts viven en ficheros

Los prompts del curso no están dentro del código: están en la carpeta `prompts/`, en ficheros Markdown que puedes leer, copiar y adaptar. Por ejemplo, `prompts/tickets/completo.md`:

```markdown
---
version: 1
descripcion: Rol, contexto, criterios de cada valor y formato.
variables: ticket
---

## Sistema

Eres el sistema de triaje de incidencias de una plataforma de comercio electrónico.
...

## Usuario

Ticket:
{{ticket}}
```

`curso_core` los carga y rellena las variables. En la lección 05 verás por qué conviene tratarlos como código.

## Práctica

[`anatomia.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/anatomia.py) clasifica los 10 tickets de evaluación con tres variantes del mismo prompt, que van sumando piezas:

1. [`tickets/minimo`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/minimo.md): el ticket y "clasifica este ticket de soporte".
2. [`tickets/con-formato`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/con-formato.md): además, el formato de respuesta y los valores posibles.
3. [`tickets/completo`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/completo.md): además, rol, contexto y los criterios de cada categoría y severidad.

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/02-prompting/anatomia.py
```

Primero muestra cómo responde cada variante al ticket 1. Sin formato, el modelo escribe un ensayo:

```text
[tickets/minimo@v1] primera respuesta:
Este ticket de soporte parece estar relacionado con un problema de conexión a un servicio de pago
en una aplicación o sistema. Aquí hay algunas consideraciones clave:

1. La fecha y hora de inicio del problema (9:40) sugiere que el problema podría estar relacionado
con la carga o la capacidad del sistema.

2. La respuesta 'too many connections' en los logs Postgres sugiere que hay un problema con la
capacidad de conexión a la base de datos Postgres.
...
```

Con formato, contesta lo que pediste, aunque no siempre bien:

```text
[tickets/con-formato@v1] primera respuesta:
categoria: rendimiento
severidad: alta
servicio: pagos

[tickets/completo@v1] primera respuesta:
categoria: base_de_datos
severidad: critica
servicio: pagos
```

Y después, el resultado de los diez tickets:

```text
variante                   utilizables categoría severidad servicio las 3 tokens latencia
tickets/minimo@v1                 0/10       0/10       0/10      0/10   0/10     74    4.04s
tickets/con-formato@v1           10/10       5/10       4/10      9/10   3/10    145    0.91s
tickets/completo@v1               8/10       6/10       4/10      7/10   3/10    345    1.08s
```

Para ver ticket a ticket qué respondió cada variante, añade `--detalle`:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/02-prompting/anatomia.py --detalle
```

```text
[tickets/completo@v1]
  1 OK   esperado base_de_datos/critica/pagos -> categoria: base_de_datos / severidad: critica / servicio: pagos
  2 NULO esperado autenticacion/media/usuarios -> categoria: otro / severidad: baja / servicio: autenticacion
  ...
  6 NULO esperado red/alta/notificaciones -> categoria: red / severidad: alta / servicio: despliegue
```

## Mide y depura

### Dos números, no uno

La práctica mide dos cosas distintas, y conviene no mezclarlas:

- **Utilizables**: respuestas con el formato pedido y valores válidos. Es lo que necesita tu código para no romperse.
- **Aciertos**: de esas, cuántas coinciden con la clasificación esperada. Es la calidad.

El prompt mínimo falla en lo primero: ninguna respuesta se puede usar, aunque el ensayo del modelo menciona Postgres y conexiones. Pedir un formato explícito pasa de 0 a 10 respuestas utilizables. **El formato es la pieza que más aporta**, y la más barata.

### Lo que no mejoró

El prompt completo añade rol, contexto y criterios. Cuesta 345 tokens de entrada por ticket, frente a 145. Y el resultado apenas cambia: 8 respuestas utilizables en lugar de 10, una categoría acertada más (6 frente a 5) y los mismos 3 tickets con los tres campos correctos.

Mira el detalle. En los tickets 2 y 6, el modelo pone una categoría en el campo del servicio (`servicio: autenticacion`, `servicio: despliegue`). Con tantas listas de valores en el prompt, un modelo de 1.5B mezcla los campos. A cambio, acierta el ticket 1 (`base_de_datos/critica`), que la variante con formato falla. Los criterios ayudan en unos casos y estorban en otros.

### La severidad es lo difícil

En las dos variantes, solo 4 de 10 severidades son correctas. El modelo tiende a rebajarlas: a casi todo le pone `alta` o `media`, incluso a los tickets en los que se pierde dinero o el servicio está caído para todos. Leer criterios no le basta. En la lección siguiente probarás otra herramienta: enseñarle ejemplos.

### La latencia la decide la salida

Fíjate en la última columna. El prompt completo tiene más del doble de tokens de entrada y apenas tarda más (1,08 s frente a 0,91 s). El mínimo, con la mitad de tokens de entrada, es el más lento con diferencia (4,04 s), porque responde con un ensayo. Las tres cifras incluyen cargar el modelo una vez: el script lo descarga antes de cada variante para que todas partan del mismo estado (verás por qué en la lección siguiente). Procesar la entrada es barato; generar la salida, no (módulo 1).

## Errores frecuentes

**No pedir un formato.** El modelo responderá como le parezca, y tu código tendrá que adivinar. Define siempre la forma exacta de la respuesta y los valores posibles.

**Dar por bueno el prompt "más profesional".** Más texto, más listas y más reglas no garantizan mejores resultados, sobre todo con modelos pequeños. Quita piezas y mide.

**Juzgar un prompt por un ejemplo.** En el ticket 1, el prompt completo acierta y el de formato falla. Con ese único caso, habrías elegido el completo. Con los diez, empatan en aciertos completos y el completo da menos respuestas utilizables.

**Etiquetas discutibles.** En el ticket 5 (una errata en el email de bienvenida), la respuesta esperada es `notificaciones`, pero el texto no nombra ningún servicio y cada variante elige uno distinto. Cuando un caso es ambiguo, el problema puede estar en el caso, no en el modelo. Lo tratarás en el módulo de evals.

### Anatomía de un error: el valor que no está en la lista

El prompt completo responde al ticket 2 con:

```text
categoria: otro
severidad: baja
servicio: autenticacion
```

Si validas esa respuesta con el esquema de la clasificación (un modelo de Pydantic con los valores permitidos en cada campo), obtienes:

```text
pydantic_core._pydantic_core.ValidationError: 1 validation error for Clasificacion
servicio
  Input should be 'pagos', 'usuarios', 'catalogo', 'notificaciones' or 'busqueda' [type=literal_error, input_value='autenticacion', input_type=str]
```

**Cómo leerlo.** Pydantic dice qué campo falla (`servicio`), qué valores admite y qué recibió (`input_value='autenticacion'`). El tipo `literal_error` indica que el valor no está en la lista cerrada de opciones.

**Causa.** `autenticacion` es un valor válido, pero de otro campo: es una categoría. El modelo ha mezclado las listas del prompt. Con texto libre, nada le impide escribir lo que quiera en cada línea.

**Solución.** Valida siempre la respuesta antes de usarla: así detectas el error en lugar de propagarlo. Para evitarlo de raíz, restringe la salida al esquema desde el servidor, de modo que el modelo no pueda escribir un valor fuera de la lista. Es la salida estructurada de la lección 03.

## Para profundizar

- [Ingeniería de prompts](https://huggingface.co/docs/transformers/tasks/prompting) en la documentación de Transformers de Hugging Face: buenas prácticas y ejemplos.
- [Plantillas de chat](https://huggingface.co/docs/transformers/chat_templating): cómo se convierten los mensajes de sistema y usuario en la entrada del modelo.
- [Modelos y validación en Pydantic](https://docs.pydantic.dev/latest/concepts/models/), incluidos los campos con una lista cerrada de valores (`Literal`).

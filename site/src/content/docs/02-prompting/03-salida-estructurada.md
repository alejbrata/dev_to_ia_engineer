---
title: "Salida estructurada"
description: "Salida estructurada: JSON Schema y Pydantic"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el modelo con el que se construyó el curso (Qwen2.5 1.5B Instruct en Ollama). La salida estructurada con esquema la admiten Ollama y muchas APIs compatibles con OpenAI, pero no todos los modelos ni todos los proveedores: compruébalo en la documentación del tuyo.
:::

## Objetivos

Al terminar esta lección podrás:

- Explicar la diferencia entre pedir JSON en el prompt e imponer un esquema desde el servidor.
- Generar un JSON Schema a partir de un modelo de Pydantic y usarlo para restringir la respuesta.
- Validar siempre la respuesta antes de usarla y distinguir sus tres fallos: JSON inválido, fuera del esquema y cortado.
- Explicar qué garantiza un esquema y qué no.

## Teoría

### Pedir no es garantizar

Hasta ahora, el formato de la respuesta dependía de que el modelo hiciera caso al prompt. Con un buen prompt, casi siempre lo hace. Pero "casi siempre" no es un contrato. En un sistema que procesa miles de tickets, el 1 % que no cumple el formato es un flujo constante de errores.

La **salida estructurada** cambia quién garantiza el formato. Le pasas al servidor un **JSON Schema** (una descripción formal de la estructura que quieres: claves, tipos, valores permitidos) y el servidor **restringe la generación**: en cada paso, solo deja elegir tokens que mantengan la respuesta dentro del esquema. Si el esquema dice que `severidad` solo puede ser `baja`, `media`, `alta` o `critica`, el modelo no puede escribir `Muy Alta`, aunque sea lo que habría elegido.

Si vienes de backend, es la diferencia entre documentar el formato de una API en una wiki y validarlo con un esquema en el gateway.

### El esquema sale de Pydantic

No hace falta escribir el JSON Schema a mano. La clasificación de los tickets ya es un modelo de Pydantic:

```python
class Clasificacion(BaseModel):
    categoria: Literal["base_de_datos", "red", "despliegue", "autenticacion", "rendimiento", "otro"]
    severidad: Literal["baja", "media", "alta", "critica"]
    servicio: Literal["pagos", "usuarios", "catalogo", "notificaciones", "busqueda"]
```

`Clasificacion.model_json_schema()` genera el esquema, con los `Literal` convertidos en listas de valores permitidos (`enum`). Así, una sola definición sirve para pedir y para validar.

### Cómo se hace en `curso_core`

`ClienteLLM.extraer` hace las tres cosas de una vez:

```python
clasificacion, respuesta = cliente.extraer(mensajes, Clasificacion)
```

1. Genera el esquema desde el modelo de Pydantic.
2. Se lo pasa al servidor en el formato de cada API (`format` en Ollama, `response_format` en las compatibles con OpenAI).
3. Valida la respuesta con Pydantic y te devuelve un objeto `Clasificacion`, o lanza `ErrorFormato` con el texto recibido.

### Lo que un esquema no hace

Un esquema garantiza la **forma** de la respuesta, no que sea **correcta**. Si el modelo cree que una base de datos caída es un problema de red, el esquema le dejará escribir `"categoria": "red"`, porque es un valor válido. La calidad sigue dependiendo del prompt y de los ejemplos (lecciones 01 y 02).

## Práctica

[`salida_estructurada.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/salida_estructurada.py) prueba dos prompts, cada uno sin esquema y con él:

- [`tickets/json-minimo`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/json-minimo.md): "Responde en JSON con las claves categoria, severidad y servicio". Sin valores posibles ni criterios.
- [`tickets/json`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/json.md): el prompt completo de la lección 01, pidiendo JSON.

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/02-prompting/salida_estructurada.py
```

```text
prompt                 esquema  válidos JSON inválido fuera del esquema  las 3
tickets/json-minimo@v1 no          0/10         10/10              0/10   0/10
tickets/json-minimo@v1 sí         10/10          0/10              0/10   1/10
tickets/json@v1        no         10/10          0/10              0/10   2/10
tickets/json@v1        sí         10/10          0/10              0/10   2/10

Primera respuesta de cada caso:
  [tickets/json-minimo@v1, esquema no] '```json\n{\n  "categoria": "Sistema de Pagos",\n  "severidad": "Muy Alta",\n  "servicio": "Soporte de Servicios"\n}\n```'
  [tickets/json-minimo@v1, esquema sí] '{\n  "categoria": "red",\n  "severidad": "media",\n  "servicio": "pagos"\n}'
  [tickets/json@v1, esquema no] '{\n  "categoria": "base_de_datos",\n  "severidad": "critica",\n  "servicio": "pagos"\n}'
  [tickets/json@v1, esquema sí] '{\n  "categoria": "base_de_datos",\n  "severidad": "critica",\n  "servicio": "pagos"\n}'
```

Lee las cuatro filas:

1. **Prompt mínimo, sin esquema.** Ninguna de las diez respuestas es JSON válido. La primera, por ejemplo, viene envuelta en un bloque de código de Markdown y con valores inventados (`"Sistema de Pagos"`, `"Muy Alta"`).
2. **Prompt mínimo, con esquema.** Diez de diez válidas, con valores de la lista. Pero solo una correcta: el esquema no sabe qué es una severidad crítica.
3. **Prompt completo, sin esquema.** Diez de diez válidas. Con un buen prompt, este modelo ya cumple el formato.
4. **Prompt completo, con esquema.** El mismo resultado, pero ahora garantizado por el servidor, no por la buena voluntad del modelo.

## Mide y depura

### Tres fallos distintos

Cuando una respuesta estructurada falla, puede hacerlo de tres formas, y cada una pide una solución distinta:

| Fallo | Qué ves | Qué hacer |
| --- | --- | --- |
| JSON inválido | El texto no se puede parsear (bloque de código, frase delante, JSON cortado) | Imponer un esquema; revisar `max_tokens` |
| Fuera del esquema | JSON válido, pero con una clave o un valor que no admites | Imponer el esquema; afinar el modelo de Pydantic |
| Incorrecto | Válido y dentro del esquema, pero equivocado | Mejorar el prompt y los ejemplos, y medirlo |

La práctica cuenta los tres por separado. Si solo cuentas "falló", no sabes qué arreglar.

### Valida siempre

Aunque el servidor imponga el esquema, valida la respuesta. El servidor puede no admitir algún detalle del esquema, el proveedor puede cambiar, o la respuesta puede cortarse, como verás en la anatomía. `extraer` valida siempre con Pydantic: lo que devuelve es un objeto que cumple el modelo, o una excepción que lo dice.

### Tokens de salida

JSON es más verboso que tres líneas de texto: llaves, comillas, sangrías. Con este prompt, unos 29 tokens de salida frente a los 17 del formato de líneas. Es poco por respuesta, pero en un proveedor de pago se nota en volumen, y la salida es la parte cara (módulo 1).

## Errores frecuentes

**Limpiar el JSON a mano.** Quitar los ` ```json ` con una expresión regular, recortar la frase de antes, cambiar comillas... Funciona hasta que el modelo responde de una forma que tu limpieza no contempla. Si tu servidor admite esquemas, úsalos.

**Confundir válido con correcto.** Diez de diez respuestas válidas con una sola correcta (la segunda fila de la práctica). El esquema arregla la forma; el contenido sigue necesitando un buen prompt y medición.

**Un esquema demasiado blando.** Si `severidad` fuera un `str` en lugar de un `Literal`, el esquema dejaría pasar `"Muy Alta"`. Restringe en el modelo de Pydantic todo lo que tu código necesite controlar.

**Olvidar `max_tokens`.** Un límite pensado para tres líneas puede cortar un JSON a la mitad. Lo ves abajo.

### Anatomía de un error: el JSON cortado

La práctica termina pidiendo la misma clasificación con el esquema impuesto, pero con `max_tokens=12`:

```text
Esquema impuesto, pero max_tokens=12:
  motivo de fin: length · texto recibido: '{\n  "categoria": "base_de_datos",\n  "'
  La respuesta no cumple Clasificacion: 1 validation error for Clasificacion
    Invalid JSON: EOF while parsing a string at line 3 column 3 [type=json_invalid, input_value='{\n  "categoria": "base_de_datos",\n  "', input_type=str]
```

**Cómo leerlo.** El error es de Pydantic, de tipo `json_invalid`: el texto ni siquiera es JSON. `EOF while parsing a string` significa que el texto se acabó (EOF, fin de fichero) en mitad de una cadena, en la línea 3. La pista definitiva está arriba: `motivo de fin: length`.

**Causa.** El servidor restringe los tokens que el modelo puede elegir, pero no el número de tokens. Con 12 tokens, el modelo empieza un JSON válido y se queda sin espacio a mitad. El esquema no protege contra un corte.

**Solución.** Da a la salida espacio de sobra para el JSON más largo que esperas, y comprueba siempre el motivo de fin: un `length` significa que la respuesta está incompleta, sea cual sea su formato. `curso_core` lo expone en `Respuesta.motivo_fin` y, cuando la validación falla, en `ErrorFormato.respuesta`.

## Para profundizar

- [JSON Schema](https://json-schema.org/learn/getting-started-step-by-step): la especificación y su guía de inicio.
- [JSON Schema en Pydantic](https://docs.pydantic.dev/latest/concepts/json_schema/): cómo se genera el esquema desde un modelo.
- [Salida estructurada en Ollama](https://docs.ollama.com/capabilities/structured-outputs): el parámetro `format` con un esquema.
- Willard y Louf, [Efficient Guided Generation for Large Language Models](https://arxiv.org/abs/2307.09702) (2023). Cómo se restringe la generación a una gramática o un esquema.

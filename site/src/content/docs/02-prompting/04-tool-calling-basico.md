---
title: "Tool calling básico"
description: "Tool calling básico"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el modelo con el que se construyó el curso (Qwen2.5 1.5B Instruct) y uno mayor de la misma familia (Qwen2.5 7B Instruct), en Ollama. La capacidad de usar herramientas varía mucho entre modelos: compruébala con el tuyo.
:::

## Objetivos

Al terminar esta lección podrás:

- Explicar qué es el tool calling y quién ejecuta realmente la herramienta.
- Definir una herramienta con un modelo de Pydantic y ofrecérsela al modelo.
- Completar un viaje de ida y vuelta: el modelo pide la herramienta, tu código la ejecuta y le devuelve el resultado.
- Validar los argumentos que propone el modelo antes de ejecutar nada.

## Teoría

### El modelo no ejecuta nada

El nombre engaña: con tool calling (o function calling), **el modelo no ejecuta ninguna herramienta**. Lo que hace es responder, en lugar de con texto, con una petición estructurada: "quiero llamar a `estado_servicio` con `servicio=pagos`". Tu código decide si la ejecuta, la ejecuta y le devuelve el resultado en un mensaje nuevo. Luego el modelo sigue, ya con esa información.

```text
tu código ──(ticket + herramientas disponibles)──▶ modelo
tu código ◀──(llamada: estado_servicio(pagos))──── modelo
tu código ── ejecuta la función ──▶ "caído: 100 % de errores 500"
tu código ──(resultado de la herramienta)────────▶ modelo
tu código ◀──(clasificación final)──────────────── modelo
```

Si vienes de backend, piensa en el modelo como en un cliente que te manda peticiones a una API que tú expones. Como con cualquier cliente externo, **validas lo que te pide antes de hacerlo**.

### Para qué sirve

Una herramienta le da al modelo lo que no está en su entrenamiento ni en el prompt: datos actuales (el estado de un servicio, un pedido, el tiempo) o acciones (abrir una incidencia, mandar un email). En este caso, el modelo puede consultar si el servicio afectado está caído o degradado antes de decidir la severidad, que era el campo más difícil del módulo.

### Cómo se define una herramienta

Una herramienta es un nombre, una descripción y el esquema de sus argumentos. Con `curso_core`, los argumentos son un modelo de Pydantic, igual que en la salida estructurada:

```python
class ArgsEstado(BaseModel):
    servicio: Literal["pagos", "usuarios", "catalogo", "notificaciones", "busqueda"]

HERRAMIENTA = Herramienta.desde(
    "estado_servicio",
    "Devuelve el estado actual de un servicio de la plataforma (operativo, degradado o caído).",
    ArgsEstado,
)

respuesta = cliente.chat(mensajes, opciones=Opciones(herramientas=[HERRAMIENTA]))
respuesta.llamadas   # [LlamadaHerramienta(nombre="estado_servicio", argumentos={"servicio": "pagos"})]
```

La descripción importa: es lo único que el modelo sabe de la herramienta. Escríbela como la documentación de un endpoint.

Para devolverle el resultado, se añaden dos mensajes a la conversación: la respuesta del modelo con su petición (`respuesta.como_mensaje()`) y un mensaje de rol `tool` con el resultado. Las dos APIs del curso lo hacen distinto por debajo (la compatible con OpenAI exige un identificador por llamada), y `curso_core` lo resuelve por ti.

### Un solo paso

Esta lección hace un único viaje de ida y vuelta: una petición, una ejecución, una respuesta final. Cuando el modelo encadena varias herramientas, decidiendo en cada paso qué hacer después, ya es un agente. Lo construirás desde cero en el módulo 5.

## Práctica

[`herramientas.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/herramientas.py) ofrece la herramienta `estado_servicio` al clasificar cada ticket, con el prompt [`tickets/con-herramienta`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/con-herramienta.md), que le pide consultar el estado antes de decidir. La herramienta lee una **página de estado simulada**: un diccionario con el estado de cada servicio. En un sistema real sería una llamada a tu monitorización; el viaje de ida y vuelta es el mismo.

Compara el modelo del curso con el de 7B (lección 05 del módulo 1). Tarda unos dos minutos:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/02-prompting/herramientas.py --detalle
```

```text
modelo          llama args válidos servicio ok  las 3
qwen2.5:1.5b     0/10         0/10        0/10   3/10
qwen2.5:7b       9/10         8/10        8/10   9/10

  [qwen2.5:1.5b]  1 sin llamada => base_de_datos/critica/pagos
  [qwen2.5:1.5b]  2 sin llamada => NULO: 'categoria: otro\nseveridad: baja\nservicio: autenticacion'
  ...
  [qwen2.5:7b]  1 estado_servicio({'servicio': 'pagos'}) -> 'caído: el 100 % de las peticiones devuelve error 500' => base_de_datos/critica/pagos
  [qwen2.5:7b]  2 estado_servicio({'servicio': 'autenticacion'}) -> "Error en los argumentos: Input should be 'pagos', 'usuarios', 'catalogo', 'notificaciones' or 'busqueda'" => NULO: 'categoria: autenticacion\nseveridad: media\nservicio: autenticacion'
  ...
  [qwen2.5:7b]  5 sin llamada => otro/baja/notificaciones
  ...
  [qwen2.5:7b]  7 estado_servicio({'servicio': 'usuarios'}) -> 'degradado: errores en parte de las peticiones' => base_de_datos/alta/usuarios
```

Las columnas cuentan, de diez tickets: cuántas veces el modelo pidió la herramienta, cuántas con argumentos válidos, cuántas con el servicio correcto y cuántas clasificaciones finales fueron correctas en los tres campos.

## Mide y depura

### El modelo pequeño no usa la herramienta

El modelo de 1.5B no la pide ni una vez. Responde directamente, como si la herramienta no existiera, y su resultado es el mismo que sin ella (3 de 10). El prompt le dice que la consulte, pero usar herramientas es una habilidad que los modelos pequeños tienen poco desarrollada. No lo arregla un prompt mejor: es una limitación del modelo.

### ¿Cuánto aporta la herramienta?

El de 7B la usa en 9 de 10 tickets y acierta 9 clasificaciones. Antes de atribuírselo a la herramienta, hay que medir lo que hace el mismo modelo **sin** ella. Con el prompt completo de la lección 01, el de 7B acierta 8 de 10:

| Modelo | Sin herramienta | Con herramienta |
| --- | --- | --- |
| 1.5B | 3/10 | 3/10 (no la usa) |
| 7B | 8/10 | 9/10 |

Casi toda la mejora viene del modelo, no de la herramienta. La herramienta aporta un acierto: en el ticket 7, saber que el servicio de usuarios está "degradado" (y no caído) le hace elegir la severidad `alta` en lugar de `critica`. Con diez casos, un acierto puede ser ruido (lección 02). Si no hubieras medido el modelo sin herramienta, habrías atribuido a la herramienta un salto de 3 a 9 que en realidad es de 8 a 9.

### Lee la traza de cada llamada

El modo `--detalle` muestra, para cada ticket, qué pidió el modelo, qué le devolviste y qué respondió al final. Es la información que necesitas para depurar el tool calling: casi todos sus fallos están en los argumentos o en lo que el modelo hace con el resultado, no en la herramienta.

## Errores frecuentes

**Creer que el modelo ejecuta la herramienta.** La ejecutas tú. Eso significa que tú controlas qué se ejecuta, con qué permisos y con qué argumentos. No ejecutes nada que no hayas validado.

**Dar por hecho que el servidor valida los argumentos.** El esquema de la herramienta declara que `servicio` solo admite cinco valores, y el modelo de 7B mandó `autenticacion`. A diferencia de la salida estructurada (lección 03), Ollama no restringe los argumentos de las herramientas al esquema. El esquema describe; no obliga.

**Herramientas mal descritas.** El modelo solo ve el nombre, la descripción y el esquema. Una descripción vaga produce llamadas vagas.

**Medir con y sin herramienta con modelos distintos.** Compara siempre el mismo modelo con y sin la herramienta, o confundirás la mejora del modelo con la de la herramienta.

### Anatomía de un error: el argumento que el esquema no impidió

En el ticket 2 (un fallo del login con Google), el modelo de 7B pide:

```text
estado_servicio({'servicio': 'autenticacion'})
```

Tu código valida los argumentos con `ArgsEstado` antes de ejecutar, y la validación falla. El error vuelve al modelo como resultado de la herramienta:

```text
"Error en los argumentos: Input should be 'pagos', 'usuarios', 'catalogo', 'notificaciones' or 'busqueda'"
```

Y la respuesta final del modelo es:

```text
categoria: autenticacion
severidad: media
servicio: autenticacion
```

**Cómo leerlo.** Hay dos fallos encadenados. Primero, un argumento fuera del esquema: `autenticacion` es una categoría, no un servicio. Segundo, el modelo recibe un error que le dice exactamente qué valores son válidos y, aun así, repite `servicio: autenticacion` en la respuesta final. No se corrige.

**Causa.** El modelo tiene una idea propia de cómo es el sistema: para él, el login es un servicio de autenticación. Ni el esquema de la herramienta (que Ollama no aplica) ni el mensaje de error cambian esa idea. Es el mismo error de la lección 01 (mezclar categorías y servicios), ahora dentro de una herramienta.

**Solución.** Lo que hizo bien el código: validar antes de ejecutar. Si la herramienta hubiera sido "reiniciar servicio", ejecutarla con un argumento inventado habría sido un problema real. Para la respuesta final, impón el esquema con salida estructurada (lección 03), que sí es obligatorio. Y si un argumento inválido se repite, no reintentes indefinidamente: marca el caso para revisión. En el módulo de agentes verás cómo limitar estos bucles.

## Bitácora

TODO(alex)

## Para profundizar

- [Tool calling en Ollama](https://docs.ollama.com/capabilities/tool-calling): definición de herramientas y mensajes de resultado.
- [Function calling en la API de OpenAI](https://platform.openai.com/docs/guides/function-calling): el formato que siguen las APIs compatibles.
- Schick et al., [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761) (2023). Uno de los trabajos que abrió el uso de herramientas por modelos de lenguaje.

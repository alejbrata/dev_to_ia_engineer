---
title: "Modelos abiertos y cerrados"
description: "Modelos abiertos frente a cerrados; primer contacto con Hugging Face"
---

:::note[Revisado: 2026-10]
Las medidas de esta lección son reales: tres tamaños de la familia Qwen2.5 en Ollama, en un equipo con 31 GB de RAM y sin GPU. Los datos del Hub (licencias, descargas) son los publicados en la fecha de revisión.
:::

## Objetivos

Al terminar esta lección podrás:

- Distinguir un modelo de pesos abiertos de uno cerrado, y un modelo local de uno alojado por un proveedor.
- Leer la ficha de un modelo en Hugging Face: licencia, tamaño y modelo base.
- Medir aciertos, latencia y memoria de varios modelos con las mismas preguntas.
- Justificar la elección de un modelo con datos de tu caso, no con su fama.

## Teoría

### Dos preguntas distintas

"¿Abierto o cerrado?" mezcla dos preguntas que conviene separar:

1. **¿Puedes descargar los pesos?** Un modelo de **pesos abiertos** publica sus pesos: los descargas y los ejecutas donde quieras. Un modelo **cerrado** solo se usa a través de la API de quien lo creó.
2. **¿Dónde se ejecuta?** En tu máquina o tu infraestructura (**local**), o en los servidores de un proveedor (**alojado**).

Combinadas, salen cuatro casillas:

| | Local | Alojado por un proveedor |
| --- | --- | --- |
| **Pesos abiertos** | Ollama con el modelo del curso | El mismo tipo de modelo, servido por un proveedor a través de Hugging Face Inference Providers |
| **Pesos cerrados** | Prácticamente no existe | Las APIs comerciales de los grandes laboratorios |

Un detalle de vocabulario: "abierto" casi siempre significa **pesos abiertos**, no código abierto en sentido estricto. Muchos modelos abiertos no publican sus datos de entrenamiento ni todo el código para reproducirlos. Puedes usarlos, pero no auditarlos de punta a punta.

### Qué te da cada opción

| | Pesos abiertos en local | Modelo alojado (abierto o cerrado) |
| --- | --- | --- |
| Datos | No salen de tu infraestructura | Viajan al proveedor |
| Coste | Fijo: hardware y energía | Variable: por token |
| Calidad | Limitada por el modelo que puedas ejecutar | Acceso a los modelos más grandes |
| Operación | La haces tú | La hace el proveedor |
| Control | Total: versión, parámetros, disponibilidad | El proveedor puede cambiar o retirar el modelo |

Sin humo: los modelos cerrados más grandes suelen rendir mejor en tareas difíciles y abiertas. Pero un modelo abierto pequeño puede bastar para tareas acotadas (clasificar, extraer, reformular), y entonces gana en coste, privacidad y control. La única forma de saberlo es medir con tus propias preguntas. Esta lección empieza a hacerlo.

### Licencias: abierto no significa "haz lo que quieras"

Cada modelo abierto tiene su licencia, y no todas son iguales:

- **Permisivas** (Apache 2.0, MIT): uso comercial libre, con atribución.
- **Propias del fabricante**: pueden limitar el uso comercial, exigir condiciones a partir de cierto número de usuarios o prohibir ciertos usos.

La licencia puede cambiar dentro de la misma familia. En la práctica lo verás: de cuatro tamaños de Qwen2.5, tres son Apache 2.0 y uno tiene una licencia propia.

### Hugging Face Hub

El [Hub de Hugging Face](https://huggingface.co/models) es el gran repositorio de modelos abiertos, con más cosas además de modelos (datasets, demos). Cada modelo es un repositorio git con:

- **Los pesos**, normalmente en formato `safetensors`, o en `GGUF` para servidores como Ollama y llama.cpp.
- **El tokenizador**: el `tokenizer.json` que ya descargaste en la lección 01.
- **La ficha (model card)**: licencia, idiomas, cómo se entrenó, limitaciones conocidas y, a veces, resultados en benchmarks.

Ollama tiene su propia biblioteca de modelos ya empaquetados, pero muchos vienen del Hub, y puede ejecutar directamente modelos GGUF de él. Por eso, aunque uses Ollama, la ficha de Hugging Face es la fuente que tienes que leer.

## Práctica

### 1. Lee las fichas

[`ficha_modelo.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/ficha_modelo.py) consulta la API del Hub y resume la ficha de cada modelo de `config/models.toml`:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/ficha_modelo.py
```

```text
Qwen/Qwen2.5-1.5B-Instruct
  licencia:    apache-2.0
  parámetros:  1.54 mil millones
  tarea:       text-generation
  descargas:   4.516.493 (último mes)
  basado en:   Qwen/Qwen2.5-1.5B

Qwen/Qwen2.5-0.5B-Instruct
  licencia:    apache-2.0
  parámetros:  0.49 mil millones
  ...

Qwen/Qwen2.5-7B-Instruct
  licencia:    apache-2.0
  parámetros:  7.62 mil millones
  ...
```

Fíjate en "basado en": cada modelo **Instruct** es un modelo base ajustado para seguir instrucciones. Ahora mira el tamaño que falta en la familia:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/ficha_modelo.py Qwen/Qwen2.5-3B-Instruct
```

```text
Qwen/Qwen2.5-3B-Instruct
  licencia:    other  <- revisa las condiciones
  parámetros:  3.09 mil millones
  tarea:       text-generation
  descargas:   3.333.473 (último mes)
  basado en:   Qwen/Qwen2.5-3B
```

Misma familia, mismo fabricante, otra licencia. Abre su página en el Hub y lee las condiciones: es lo que tendrías que hacer antes de usarlo en un producto. Por eso el curso compara 0.5B, 1.5B y 7B.

### 2. Compara tres tamaños

Descarga los dos modelos que faltan (unos 5 GB entre los dos):

```sh title="Cualquier terminal"
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:7b
```

[`comparar_modelos.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/comparar_modelos.py) hace las mismas cinco preguntas, con respuesta comprobable, a los tres modelos (roles `chat_pequeno`, `chat` y `chat_grande`):

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/comparar_modelos.py
```

```text
[qwen2.5:0.5b]
  OK      0.1 s  'azul.'
  OK      0.1 s  'Canberra'
  OK      0.1 s  '391'
  FALLO   1.0 s  'Un balanceador de carga es un componente fundamental en la arquitectur'
  OK      0.2 s  'The message queue decouples the services.'

[qwen2.5:1.5b]
  FALLO   0.2 s  'blanco.'
  OK      0.2 s  'Canberra'
  OK      0.2 s  '391'
  OK      1.3 s  'Un balanceador de carga en una arquitectura web sirve para distribuir '
  OK      0.4 s  'The queue of messages decouples the services.'

[qwen2.5:7b]
  OK      0.7 s  'azul'
  OK      0.7 s  'Canberra'
  OK      0.9 s  '391'
  OK      4.0 s  'Un balanceador de carga distribuye la carga de tráfico entre múltiples'
  OK      1.7 s  'The message queue decouples services.'

modelo            aciertos  latencia media  tokens/s  memoria
qwen2.5:0.5b        4 de 5           0.3 s      65.1   0.49 GB
qwen2.5:1.5b        4 de 5           0.4 s      28.6   1.17 GB
qwen2.5:7b          5 de 5           1.6 s       5.8   5.07 GB
```

## Mide y depura

### Leer la tabla

- **Calidad.** Solo el de 7B acierta todo. El de 1.5B, el del curso, vuelve a decir que el cielo despejado es blanco (lección 01). El de 0.5B sí acierta el color, pero falla en el balanceador.
- **Latencia.** El de 7B tarda unas cuatro veces más que el de 1.5B de media. En la pregunta abierta del balanceador, 4 s frente a 1,3 s.
- **Memoria.** Unas diez veces más de 0.5B a 7B. En un equipo sin GPU, el de 7B ya se nota; uno de 70B no cabría.

No hay un ganador absoluto. Si tu tarea son respuestas cortas y comprobables, un modelo pequeño puede acertar casi lo mismo a una fracción del coste y la memoria. Si son explicaciones abiertas, el grande se nota. Decide con tus preguntas, no con las de otros.

### Mira los fallos uno a uno

Un "FALLO" no siempre es culpa del modelo: también puede fallar el comprobador. Antes de sacar conclusiones, lee la respuesta entera. La del modelo de 0.5B sobre el balanceador fue esta:

```text
Un balanceador de carga es un componente fundamental en la arquitectura web que ayuda a optimizar la carga de los sitios web y alinear la carga de los usuarios. Al balancear la carga de los sitios web, un balanceador de carga puede ayudar a reducir la carga de los sitios web en tiempo de carga, mejorar la experiencia del usuario y aumentar la velocidad de
```

Es vaga y repetitiva, ignora el "una frase" y se corta al llegar a los 80 tokens (su `motivo_fin` fue `length`). El fallo es legítimo. Con otras respuestas no lo será, y lo verás al construir evals en los módulos 2 y 4.

### Cinco preguntas no son una evaluación

Con cinco preguntas, un acierto más o menos cambia la conclusión. Sirven para hacerse una idea, no para decidir. Para elegir un modelo de verdad necesitas decenas o cientos de casos representativos de tu tarea, y una forma fiable de puntuarlos. Es exactamente lo que construirás en el módulo de evals.

Ni siquiera hace falta cambiar de preguntas para que cambie el resultado. Al repasar el curso, ejecutamos esta práctica justo después de la de la lección 02, que deja el modelo de 1.5B cargado con un contexto de 8192 tokens. Esta vez acertó el color:

```text
[qwen2.5:1.5b]
  OK      0.2 s  'azul.'
```

Con 5 de 5, la tabla diría que el de 1.5B empata con el de 7B. Ejecutada otra vez, con el modelo cargado de nuevo, vuelve a decir "blanco." tres de tres veces. Es el no determinismo de la lección 03: con temperatura 0, el resultado también puede depender de cómo está cargado el modelo (es la explicación más probable; no la hemos aislado). Una sola ejecución con cinco preguntas no basta para decidir.

Fíjate también en cómo se mide la columna de tokens por segundo: tokens de salida entre tiempo total, que incluye procesar la pregunta. Con respuestas de una palabra, ese tiempo pesa mucho y la cifra baja. Entender qué mide exactamente una métrica es parte de medir.

## Errores frecuentes

**Elegir el modelo por su fama o por un ranking.** Los rankings miden tareas genéricas. Tu tarea es concreta. Mide con tus preguntas.

**Ignorar la licencia.** La licencia puede cambiar entre tamaños de la misma familia, como acabas de ver. Léela antes de que el modelo llegue a producción, no después.

**Creer que abierto es gratis.** No pagas por token, pero pagas el hardware, la energía y el tiempo de operarlo. Lo cuantificarás en la lección siguiente.

**Comparar en condiciones distintas.** Si un modelo está cargado y otro no, comparas tiempos de carga, no de respuesta. El script hace una llamada de calentamiento antes de medir cada modelo, y usa la misma temperatura y el mismo límite de tokens para todos.

### Anatomía de un error: el modelo que olvidaste descargar

Cambias el rol `chat_grande` en `config/models.toml` para probar el modelo de 3B y ejecutas la comparación:

```text
404 Not Found en http://127.0.0.1:11434/api/chat: {"error":"model 'qwen2.5:3b' not found"}
```

**Cómo leerlo.** Es un 404 a `/api/chat`, una ruta que existe. El motivo está en el cuerpo, que `curso_core` incluye en el mensaje: el modelo no se encuentra.

**Causa.** El modelo no está descargado en Ollama. Configurarlo en `models.toml` no lo descarga: son dos pasos distintos.

**Solución.** `ollama pull qwen2.5:3b` y vuelve a ejecutar. Para saber qué tienes descargado, `ollama list`. Y antes de usar ese modelo en serio, recuerda lo que viste en su ficha: su licencia no es Apache 2.0.

## Para profundizar

- [Documentación del Hub de Hugging Face](https://huggingface.co/docs/hub/index), en especial las [fichas de modelo](https://huggingface.co/docs/hub/model-cards) y las [licencias](https://huggingface.co/docs/hub/repositories-licenses).
- [`huggingface_hub`](https://huggingface.co/docs/huggingface_hub/index): la librería de Python que usa `ficha_modelo.py`.
- [Fichas de la familia Qwen2.5](https://huggingface.co/collections/Qwen/qwen25-66e81a666513e518adb90d9e) en el Hub.
- [Biblioteca de modelos de Ollama](https://ollama.com/library).

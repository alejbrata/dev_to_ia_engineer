---
title: "Ventana de contexto, límites y qué pasa cuando te pasas"
description: "Ventana de contexto, límites y qué pasa cuando te pasas"
---

:::note[Revisado: 2026-10]
Las medidas de esta lección se tomaron con el modelo con el que se construyó el curso (Qwen2.5 1.5B Instruct) en Ollama 0.40.13, en un equipo sin GPU. El comportamiento al superar el contexto no está documentado por Ollama y puede cambiar entre versiones: ejecuta la práctica para ver el de la tuya.
:::

## Objetivos

Al terminar esta lección podrás:

- Distinguir el contexto máximo de un modelo del contexto que tiene configurado el servidor.
- Explicar qué cuesta ampliar el contexto, en memoria y en latencia, con datos medidos.
- Detectar que un prompt se ha recortado comparando los tokens enviados con los procesados.
- Configurar el tamaño del contexto en Ollama y saber cuándo merece la pena.

## Teoría

### Qué es la ventana de contexto

La **ventana de contexto** es el número máximo de tokens que el modelo maneja en una llamada. Ahí cabe todo: el prompt de sistema, los mensajes de la conversación y la respuesta que está generando. Entrada y salida comparten el mismo espacio. Si el prompt ocupa casi toda la ventana, queda poco sitio para la respuesta.

Hay dos límites distintos, y conviene no confundirlos:

- **El máximo del modelo.** El que se fijó al entrenarlo. El modelo del curso admite 32 768 tokens; lo dice su ficha y lo reporta Ollama en los metadatos del modelo.
- **El que configura el servidor.** El que se usa realmente en cada llamada. Ollama, en equipos con menos de 24 GB de memoria de GPU, usa por defecto 4 096 tokens, muy por debajo del máximo del modelo.

En las APIs alojadas de los proveedores, el contexto suele venir fijado por el modelo y no lo eliges. En un servidor propio, sí, y es una decisión de capacidad como el tamaño de un pool de conexiones.

### Qué cuesta ampliarlo

Más contexto no es gratis. Mientras procesa el texto, el modelo guarda en memoria resultados intermedios por cada token de la ventana (la llamada caché KV). Cuanto más grande es la ventana, más memoria reserva, aunque no la llenes.

Además, procesar un prompt largo es lento, y el tiempo crece más deprisa que el número de tokens. En las medidas de esta lección, pasar de 6 000 a 12 700 tokens de entrada (algo más del doble) multiplicó el tiempo por 2,5.

### Qué pasa cuando te pasas

Depende del servidor, y esta es la parte peligrosa:

- **Rechazar la petición.** Es lo habitual en las APIs alojadas y en servidores como llama.cpp: devuelven un error que indica que se ha superado el contexto. Es lo mejor que te puede pasar, porque te enteras.
- **Recortar en silencio.** Es lo que hace Ollama: descarta el principio del prompt y sigue adelante sin avisar. El modelo responde con lo que le queda, y si lo importante estaba al principio, se lo inventa.
- **Limitar el valor que pides.** Si pides a Ollama más contexto del que admite el modelo (por ejemplo, 65 536 con un máximo de 32 768), lo limita al máximo sin avisar.

Las aplicaciones de chat tienen el mismo problema con las conversaciones largas: llega un momento en que los primeros mensajes ya no caben y se descartan. El modelo "olvida" el principio de la conversación.

Por último, que algo quepa no significa que se aproveche igual. Un estudio de 2023 (enlazado al final) midió que los modelos usan peor la información situada en mitad de un contexto largo que la que está al principio o al final. Tenlo en cuenta cuando decidas dónde colocar lo importante.

## Práctica

[`contexto.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/contexto.py) esconde un dato (un código de acceso) en un texto de unos 6 000 tokens y pregunta por él en tres casos. Tarda alrededor de un minuto y medio en un equipo sin GPU:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/contexto.py
```

```text
[dato al principio, contexto por defecto]
  tu texto: 6016 tokens · procesados: 2050  <- RECORTADO
  respuesta: '12345678' (FALLA)
  latencia: 14.7 s · contexto 4096 · memoria 1.17 GB

[dato al final, contexto por defecto]
  tu texto: 6016 tokens · procesados: 2050  <- RECORTADO
  respuesta: '7391' (acierta)
  latencia: 15.1 s · contexto 4096 · memoria 1.17 GB

[dato al principio, contexto 8192]
  tu texto: 6016 tokens · procesados: 6045
  respuesta: '7391' (acierta)
  latencia: 54.1 s · contexto 8192 · memoria 1.37 GB

Modelo: qwen2.5:1.5b
```

Léelo caso a caso:

1. **Dato al principio, contexto por defecto.** De 6 016 tokens, el servidor procesó 2 050. El dato estaba en la parte descartada. El modelo no dice "no lo sé": inventa un código.
2. **Dato al final, contexto por defecto.** El recorte es el mismo, pero el dato estaba en la parte que se conservó. Acierta. Si solo probaras este caso, darías el sistema por bueno.
3. **Dato al principio, contexto 8 192.** Todo cabe. Acierta, pero tarda casi cuatro veces más y usa más memoria.

Cambia el tamaño del texto con el número de párrafos (`contexto.py 100`, `contexto.py 300`) y observa dónde empieza el recorte.

### El mismo prompt en llama.cpp

Ollama no es el único servidor que puedes montar en local. [llama.cpp](https://github.com/ggml-org/llama.cpp) incluye `llama-server`, que habla la API compatible con OpenAI y se comporta como un proveedor en la nube cuando te pasas de contexto. Instálalo (en Windows, `winget install llama.cpp`; en macOS, `brew install llama.cpp`; en Linux, desde sus [releases](https://github.com/ggml-org/llama.cpp/releases)) y arráncalo con el mismo modelo, descargado directamente de Hugging Face y con 4 096 tokens de contexto:

```sh title="Terminal aparte · se queda en marcha"
llama-server -hf Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M -c 4096 --port 8081
```

La primera vez descarga el modelo (alrededor de 1 GB). Con el servidor arrancado, en otra terminal, manda el mismo texto de 6 000 tokens con [`contexto_llamacpp.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/contexto_llamacpp.py), que usa el rol `chat_llamacpp`:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/contexto_llamacpp.py
```

```text
Rechazada · status 400 · intentos 1
motivo: {"error":{"code":400,"message":"request (6045 tokens) exceeds the available context size (4096 tokens), try increasing it","type":"exceed_context_size_error","n_prompt_tokens":6045,"n_ctx":4096}}
```

Mismo modelo, mismo texto, mismo contexto configurado. Ollama recortó en silencio y el modelo se inventó el código; llama.cpp rechaza la petición y te dice exactamente cuánto te has pasado. Con un texto que cabe (`contexto_llamacpp.py 100`, unos 3 000 tokens), responde bien:

```text
Respuesta: '7391' · 3165 tokens procesados
```

El comportamiento ante el límite no depende del modelo, sino del servidor que lo sirve. Es una de las cosas que debes comprobar antes de elegir uno.

### Cómo se configura el contexto en Ollama

Por llamada, con la opción `contexto` de `curso_core` (que se traduce al parámetro `num_ctx` de Ollama):

```python
cliente.chat(prompt, opciones=Opciones(contexto=8192))
```

Para todo el servidor, con una variable de entorno al arrancarlo:

```sh title="Terminal aparte · se queda en marcha"
OLLAMA_CONTEXT_LENGTH=8192 ollama serve
```

En las aplicaciones de escritorio de Ollama también hay un ajuste para cambiarlo. Comprueba con `ollama ps` qué contexto tiene el modelo cargado: aparece en la columna `CONTEXT`.

## Mide y depura

### Tokens enviados frente a procesados

La métrica clave de esta lección es la comparación entre los tokens de tu texto y los que el servidor dice haber procesado (`tokens_entrada` en `curso_core`). Con la plantilla de chat, el servidor debería procesar siempre algo **más** que tu texto. Si procesa **menos**, ha recortado.

Es una comprobación barata que puedes dejar en el código:

```python
if respuesta.tokens_entrada < tokens_de_mi_texto:
    raise RuntimeError("El servidor ha recortado el prompt")
```

En producción prefiere un fallo explícito a una respuesta inventada.

### El coste del contexto, medido

Estas son las medidas de memoria del modelo cargado con distintos tamaños de contexto, tomadas con `ollama ps` en el mismo equipo:

| Contexto | Memoria |
| --- | --- |
| 4 096 | 1,17 GB |
| 8 192 | 1,37 GB |
| 16 384 | 1,60 GB |
| 32 768 | 2,13 GB |

Y de latencia, con temperatura 0 y respuestas de pocos tokens:

| Tokens procesados | Latencia |
| --- | --- |
| 2 050 (recortado) | ~15 s |
| 6 045 | 54 s |
| 12 733 | 138 s |

Con estos datos puedes razonar como lo harías con cualquier recurso: ¿cuánto contexto necesitan de verdad tus peticiones? Mide la distribución de `tokens_entrada` en tus trazas y dimensiona con margen, no al máximo.

### Por qué terminó la respuesta

`curso_core` devuelve también `motivo_fin`: `stop` si el modelo terminó por sí mismo y `length` si se cortó por el límite de tokens de salida. Un `length` inesperado indica que la respuesta está incompleta, a menudo porque el prompt ocupaba casi toda la ventana.

## Errores frecuentes

**Confundir el máximo del modelo con el contexto configurado.** La ficha dice 32 768 y das por hecho que caben 30 000 tokens. Pero el servidor está usando 4 096. Mira siempre el contexto real con `ollama ps` o en la configuración de tu servidor.

**Dar por hecho que todos los servidores se comportan igual.** Con el mismo modelo, Ollama recorta y llama.cpp rechaza. Si cambias de servidor, de proveedor o de versión, vuelve a comprobar qué pasa al superar el límite.

**Validar solo con casos que funcionan por casualidad.** Si tu dato de prueba está al final del texto, el recorte no se nota. Prueba con la información importante en distintas posiciones.

**Subir el contexto al máximo por si acaso.** Reserva memoria aunque no la uses y, si de verdad la llenas, multiplica la latencia. Dimensiona según lo que miden tus trazas.

**Dejar crecer el historial de chat sin control.** Cada mensaje nuevo se suma a los anteriores. Tarde o temprano, la conversación no cabe y los primeros mensajes desaparecen. Decide tú qué se conserva (resúmenes, ventana deslizante) antes de que lo decida el servidor.

### Anatomía de un error: la respuesta inventada que no dio error

El primer caso de la práctica es un error sin traza. La llamada termina bien, sin excepción ni código HTTP de error, con `motivo_fin` igual a `stop`, y el modelo responde con seguridad:

```text
respuesta: '12345678'
```

**Cómo leerlo.** Cuando no hay excepción, el error está en las métricas. El código correcto era `7391`. La respuesta es un número genérico, el típico relleno de un modelo que no tiene el dato. La pista está en la línea anterior:

```text
tu texto: 6016 tokens · procesados: 2050
```

El servidor procesó un tercio de lo que mandaste.

**Causa.** El contexto por defecto de Ollama (4 096 tokens en este equipo) era menor que el prompt. Ollama descartó el principio del texto, donde estaba el dato, sin avisar. El modelo respondió con lo que le quedaba.

**Solución.** A corto plazo, amplía el contexto (`Opciones(contexto=8192)` u `OLLAMA_CONTEXT_LENGTH`) para que quepa tu caso. A largo plazo, mide: registra los tokens procesados de cada llamada y alerta cuando sean menos que los enviados. Y no metas en el prompt más de lo necesario; en el módulo de RAG aprenderás a seleccionar solo los fragmentos relevantes.

## Bitácora

TODO(alex)

## Para profundizar

- [llama.cpp](https://github.com/ggml-org/llama.cpp): el servidor `llama-server` y su API compatible con OpenAI.
- [Context length](https://docs.ollama.com/context-length) y [preguntas frecuentes](https://docs.ollama.com/faq) en la documentación de Ollama: valores por defecto y cómo cambiarlos.
- Liu et al., [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) (2023). Por qué la posición de la información en el contexto importa.
- [Ficha de Qwen2.5 1.5B Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct): contexto máximo del modelo.

---
title: "Coste y latencia"
description: "Coste y latencia: cómo se calculan y cómo medirlos"
---

:::note[Revisado: 2026-10]
Las medidas son reales, con el modelo con el que se construyó el curso en un equipo sin GPU. Los precios son los que publicaba la API de Hugging Face en la fecha de revisión; la práctica consulta los de hoy.
:::

## Objetivos

Al terminar esta lección podrás:

- Calcular el coste de una petición y proyectarlo a millones de peticiones con tus tokens reales.
- Medir la latencia con percentiles (p50, p95) a partir de las trazas, y explicar por qué la media engaña.
- Separar el tiempo del modelo del tiempo que añade tu cliente, comparando ambas medidas.
- Reintentar ante un límite de uso respetando `Retry-After`, y medir lo que cuestan los reintentos.

## Teoría

### Cómo se calcula el coste

Un proveedor cobra por token, con dos precios distintos, normalmente en dólares por millón de tokens:

```text
coste = tokens_entrada × precio_entrada + tokens_salida × precio_salida
```

La salida suele costar varias veces más que la entrada: generar es más caro que leer. En el modelo que usarás de referencia, 0,01 $ por millón de entrada y 0,03 $ por millón de salida.

En local no hay precio por token. Pagas el hardware, la energía y el tiempo de operarlo: un coste fijo que no depende de cuánto lo uses, pero que tiene un techo de capacidad. La forma honesta de comparar es traducir tu carga a horas de máquina.

### De qué está hecha la latencia

Entre que tu código llama y recibe la respuesta pasan varias cosas, y cada una se puede medir:

1. **Conexión**: resolver el nombre del servidor y abrir la conexión. Debería ser casi nada. No siempre lo es, como verás en la anatomía del error.
2. **Carga del modelo**: solo si no estaba en memoria. Segundos.
3. **Procesar la entrada** (prefill): leer todos los tokens del prompt. Crece con el tamaño de la entrada.
4. **Generar la salida** (decode): token a token. Crece con el tamaño de la salida, y suele ser lo que más pesa.

El tiempo hasta el primer fragmento (lección 04) incluye los tres primeros. El tiempo total, los cuatro.

### Percentiles, no medias

Si nueve peticiones tardan 1 s y una tarda 20 s, la media es 2,9 s: no describe ninguna petición real. Por eso, como en cualquier APM, la latencia se mide con **percentiles**:

- **p50** (mediana): lo que tarda una petición típica.
- **p95**: lo que tarda el 5 % más lento. Es lo que sufren tus usuarios menos afortunados, y donde aparecen los problemas: reintentos, colas, recargas del modelo.

### Caché del prompt

Los servidores pueden guardar el cálculo de un prompt para reutilizarlo si vuelve a llegar igual. El efecto es enorme. Con el prompt de 6 045 tokens de la lección 02, en este equipo:

| | Tokens reutilizados | Latencia |
| --- | --- | --- |
| Primera llamada | 0 | 45,8 s |
| Misma llamada, repetida | 6 044 | 0,6 s |

Ollama lo informa en `prompt_eval_cached_count`. Muchos proveedores en la nube también tienen caché de prompt, y algunos cobran menos por los tokens reutilizados. Por eso conviene que la parte fija del prompt (instrucciones, contexto común) vaya al principio y la variable al final.

### Límites de uso y reintentos

Los proveedores limitan cuántas peticiones o tokens puedes usar por minuto. Al superarlo responden 429, a menudo con una cabecera `Retry-After` que dice cuántos segundos esperar. `curso_core` la respeta; si no viene, espera con backoff exponencial y jitter.

Los reintentos convierten un error en una respuesta lenta. Es lo que quieres, pero tiene una consecuencia: **la tasa de error no los ve**. Para detectarlos hay que mirar el p95 y contar los reintentos. `curso_core` guarda los intentos de cada llamada en su traza, y el resumen de métricas los suma.

## Práctica

### 1. Coste y latencia de una carga real

[`coste_y_latencia.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/coste_y_latencia.py) lanza 20 peticiones variadas al modelo local, resume las trazas y proyecta el coste de un millón de peticiones como esas. Tarda alrededor de un minuto:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/coste_y_latencia.py
```

```text
1. 20 peticiones al modelo local
   1.  0.97 s ·  38 +  19 tokens
   2.  5.17 s ·  48 + 150 tokens
   3.  4.61 s ·  45 + 150 tokens
  ...
  19.  4.52 s ·  46 + 150 tokens
  20.  1.81 s ·  50 +  60 tokens

  p50 4.47 s · p95 4.61 s · 32.5 tokens/s · errores 0

2. Proyección para 1.000.000 peticiones
  petición media: 46 tokens de entrada y 106 de salida
  local: 0 $ por token, pero ~1.243 horas de esta máquina en serie
  Qwen/Qwen3-4B-Instruct-2507 (models.toml): 0.01 $ / 0.03 $ por millón -> 3.63 $ por 1 millón de peticiones
  Qwen/Qwen3-4B-Instruct-2507 (publicado hoy): 0.01 $ / 0.03 $ por millón -> 3.63 $ por 1 millón de peticiones
```

Un millón de peticiones como estas costaría **3,63 $** en un proveedor que sirve un modelo de 4B. En este equipo, sin GPU y de una en una, supondría **unas 1 243 horas de máquina**: casi dos meses sin parar. Las dos cifras son reales y no se contradicen: un proveedor reparte el coste de hardware dedicado entre muchísimos clientes. En local ganas privacidad y control, no un precio más bajo por petición, salvo que tengas hardware adecuado y un volumen que lo amortice.

Fíjate también en la última línea: el script compara el precio que tienes en `models.toml` con el que publica hoy la API de Hugging Face. Si un día no coinciden, tu configuración se ha quedado vieja.

### 2. Reintentos frente a un límite de uso

Provocar un 429 real a voluntad no es fácil, así que la práctica usa un **simulador**: un servidor local de mentira, compatible con OpenAI, que deja pasar 3 peticiones cada 5 segundos y responde 429 al resto. No es un modelo: solo sirve para ver cómo se comporta tu cliente. [`reintentos.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/reintentos.py) lo arranca y le lanza 8 peticiones seguidas, con y sin `Retry-After`:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/reintentos.py
```

```text
8 peticiones seguidas, con Retry-After
  petición 1: 1 intento(s),  0.25 s
  petición 2: 1 intento(s),  0.02 s
  petición 3: 1 intento(s),  0.01 s
  petición 4: 2 intento(s),  5.02 s
  petición 5: 1 intento(s),  0.00 s
  petición 6: 1 intento(s),  0.00 s
  petición 7: 2 intento(s),  5.02 s
  petición 8: 1 intento(s),  0.00 s
  resumen: 8 llamadas, 0 errores, 2 reintentos, p50 0.01 s, p95 5.02 s

8 peticiones seguidas, sin Retry-After (backoff exponencial)
  petición 1: 1 intento(s),  0.22 s
  petición 2: 1 intento(s),  0.02 s
  petición 3: 1 intento(s),  0.02 s
  petición 4: 5 intento(s), 10.58 s
  petición 5: 1 intento(s),  0.01 s
  petición 6: 1 intento(s),  0.00 s
  petición 7: 5 intento(s),  9.16 s
  petición 8: 1 intento(s),  0.00 s
  resumen: 8 llamadas, 0 errores, 8 reintentos, p50 0.02 s, p95 10.58 s
```

Tres cosas que leer:

- **Cero errores en las dos rondas.** Si solo miraras la tasa de error, todo estaría perfecto.
- **El p95 lo delata.** De 0,01 s a 5 s con `Retry-After`, y a más de 10 s sin él.
- **`Retry-After` ahorra intentos y tiempo.** Con la cabecera, el cliente espera exactamente lo necesario: 2 intentos. Sin ella, va probando a ciegas con esperas crecientes: 5 intentos y el doble de tiempo. Cada intento de más es carga extra para un servidor que ya está saturado.

Fíjate también en la primera petición de cada ronda: tarda 0,2 s y las siguientes, casi cero. Es el coste de abrir la conexión, que `curso_core` paga una vez y reutiliza.

## Mide y depura

### El resumen de tus trazas

Todo lo que has medido en el módulo sale de las trazas de `curso_core`. Para resumir las tuyas:

```sh title="Terminal de VS Code · raíz del repo"
uv run python -c "from curso_core.metrics import resumir_por; from curso_core.tracing import leer; [print(m, r) for m, r in resumir_por(leer()).items()]"
```

Obtienes, por modelo, llamadas, errores, reintentos, p50, p95, tokens y coste. Son las cuatro métricas del curso (tokens, latencia, coste y tasa de error), más los reintentos que esconde la tercera.

### Dónde está el coste

En la proyección, la entrada media fue de 46 tokens y la salida de 106. Con los precios del proveedor, la salida supone el 87 % del coste. Y 12 de las 20 respuestas llegaron al límite de 150 tokens que puso el script (`motivo_fin` igual a `length`): sin ese límite, habrían sido más largas y más caras. **Controlar la longitud de la salida es la palanca de coste y latencia más directa que tienes.**

### Cliente frente a servidor

Ollama te dice cuánto tardó en el servidor (`total_duration`). Tu cliente mide cuánto tardó la llamada completa. Si la diferencia es grande, el tiempo se está yendo fuera del modelo: en la red, en la conexión o en tu propio código. Compáralas de vez en cuando. Fue así como apareció el error de la sección siguiente.

## Errores frecuentes

**Medir con la media.** Esconde los casos lentos, que son los que generan quejas. Usa p50 y p95.

**Calcular el coste solo con la entrada.** La salida cuesta más por token y, a menudo, tiene más tokens. Aquí era el 87 % del coste.

**No limitar la salida.** Sin `max_tokens`, un modelo hablador multiplica coste y latencia. Pon un límite acorde a lo que necesitas.

**Fiarse de la tasa de error cuando hay reintentos.** Un sistema con un 0 % de errores puede estar reintentando la mitad de sus llamadas. Mira los reintentos y el p95.

**Precios de memoria.** Los precios cambian. Guárdalos en configuración, marcados con la fecha de revisión, y compáralos con los publicados.

### Anatomía de un error: los dos segundos que no eran del modelo

Al preparar esta lección, las respuestas de una sola palabra tardaban 2,5 s. Pero en la lección 04 se había medido una velocidad de unos 37 tokens por segundo: una palabra debería tardar una fracción de segundo. Algo no cuadraba. La comparación entre cliente y servidor para la misma pregunta, repetida tres veces, dio esto:

```text
http://localhost:11434     cliente  2.42 s · servidor  0.13 s · diferencia  2.30 s
http://localhost:11434     cliente  2.49 s · servidor  0.14 s · diferencia  2.36 s
http://localhost:11434     cliente  2.43 s · servidor  0.12 s · diferencia  2.31 s
http://127.0.0.1:11434     cliente  0.41 s · servidor  0.13 s · diferencia  0.28 s
http://127.0.0.1:11434     cliente  0.40 s · servidor  0.12 s · diferencia  0.28 s
http://127.0.0.1:11434     cliente  0.40 s · servidor  0.12 s · diferencia  0.28 s
127.0.0.1, cliente reutilizado cliente  0.12 s · servidor  0.12 s · diferencia  0.00 s
127.0.0.1, cliente reutilizado cliente  0.11 s · servidor  0.11 s · diferencia  0.00 s
127.0.0.1, cliente reutilizado cliente  0.12 s · servidor  0.12 s · diferencia  0.00 s
```

**Cómo leerlo.** El servidor tardaba lo mismo en todos los casos: 0,12 s. La diferencia estaba toda en el cliente, y tenía dos partes. Con `localhost`, 2,3 s. Con `127.0.0.1`, 0,28 s. Reutilizando el cliente, nada.

**Causa.** Dos problemas acumulados:

1. En este equipo (Windows), `localhost` se resuelve primero a la dirección IPv6 `::1`. Ollama solo escucha en IPv4 (`127.0.0.1`), así que el sistema intenta IPv6, espera unos 2 segundos a que falle y entonces prueba IPv4. En cada conexión.
2. La primera versión de `curso_core` creaba un cliente HTTP nuevo en cada llamada. Cada cliente nuevo prepara su configuración de seguridad y abre una conexión desde cero: los 0,28 s restantes.

Todas las latencias medidas hasta entonces incluían esos 2,3 s, que no tenían nada que ver con el modelo.

**Solución.** Las URLs locales de `config/models.toml` usan `127.0.0.1` en lugar de `localhost`, y `curso_core` reutiliza una conexión por proveedor entre llamadas. Las cifras de las lecciones anteriores se volvieron a medir después del arreglo. La lección general: cuando una latencia no cuadra con lo que esperas, compara lo que mide el cliente con lo que mide el servidor. Si no coinciden, el problema está entre los dos.

## Para profundizar

- [Precios de Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/pricing).
- [Preguntas frecuentes de Ollama](https://docs.ollama.com/faq): cuánto tiempo mantiene un modelo cargado y cómo cambiarlo.
- [Cabecera `Retry-After`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Retry-After) y [código 429](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429) en MDN.
- AWS Architecture Blog, [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/): por qué el jitter importa cuando muchos clientes reintentan a la vez.
- [Clientes y reutilización de conexiones en httpx](https://www.python-httpx.org/advanced/clients/): por qué conviene reutilizar un cliente.

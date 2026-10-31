---
title: "G. APIs comerciales"
description: "Usar OpenAI, Claude u otro proveedor en lugar del modelo local, como opción, con su coste medido"
---

:::note[Revisado: 2026-10]
Los modelos y precios citados son los publicados por cada proveedor en octubre de 2026 y cambian a menudo: los nombres viven en `config/models.toml`. Puedes usar el proveedor y el modelo que quieras o puedas.
:::

El curso funciona entero con modelos abiertos en local, sin pagar por token. Es una decisión deliberada: cualquiera puede seguirlo, y medir con un modelo pequeño enseña más que con uno que lo hace casi todo bien. Pero en tu trabajo quizá necesites más calidad de la que da un modelo que cabe en un portátil, o no tengas máquina para el de 7B. Este anexo explica cómo cambiar cualquier práctica a una API comercial y cómo medir si compensa.

Es opcional. Nada del núcleo del curso depende de ello.

## Lo que cambia y lo que no

`curso_core` habla el formato compatible con OpenAI desde el módulo 1 (lección 04). Para el cliente, OpenAI es un proveedor más: cambia la URL, la clave y el modelo, en `config/models.toml` y `.env`, y el código de las prácticas no se toca.

Lo que sí cambia:

- **Pagas por token.** Cada pregunta cuesta dinero, y cada ejecución de una eval, también. Mídelo (abajo).
- **Tus datos salen de tu máquina.** El prompt, el contexto recuperado y la pregunta viajan al proveedor. Con documentación interna real, revisa su política de datos y la de tu empresa antes de enviar nada.
- **Dependes de un tercero**: su disponibilidad, sus límites de uso (los errores 429 del módulo 1) y sus cambios de modelos y precios.
- **Los resultados no son comparables con los publicados en el curso.** Si cambias de modelo, vuelve a medir: es el método de todo el módulo 4.

## Configurar OpenAI

1. Crea una clave en la consola de OpenAI y añade saldo a la cuenta: sin saldo, la clave es válida pero las llamadas fallan.
2. Ponla en `.env` (nunca en el código ni en `config/models.toml`):

```sh title=".env"
OPENAI_API_KEY=tu-clave
```

3. Usa uno de los dos roles que ya están en `config/models.toml`: `chat_openai` (el modelo barato) o `chat_openai_grande` (el intermedio).

El proveedor `openai` de `config/models.toml` tiene un detalle: `parametro_max_tokens = "max_completion_tokens"`. La API de OpenAI ha dejado `max_tokens` como obsoleto en favor de `max_completion_tokens`, que además no es compatible con sus modelos de razonamiento. Ollama, llama.cpp y vLLM siguen usando `max_tokens`. El cliente envía el nombre que diga cada proveedor.

Para que una práctica concreta use la API, cambia el rol que usa. Por ejemplo, para que todo lo que usa el rol `chat` vaya a OpenAI, en `config/models.toml`:

```toml title="config/models.toml"
[roles.chat]
provider = "openai"
model = "gpt-6-luna"
```

Recuerda deshacerlo: las cifras publicadas en las lecciones son con el modelo local.

## Medir si compensa

Antes de pasar un sistema a una API, mide con tu eval qué ganas y cuánto cuesta. [`con_api.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/con_api.py) responde las 58 preguntas del módulo 4 con el sistema vigente de la lección 07 (misma recuperación, mismo prompt) cambiando solo el modelo que genera. Después compara caso a caso con los resultados del modelo local y resume el coste y la latencia a partir de las trazas:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/con_api.py --rol chat_openai
```

Necesita el reranker de la lección 05 del módulo 3 en marcha, como el resto de prácticas del módulo 4. Con `--grabadas` repite el informe sin llamar a nada.

:::caution[Salida pendiente]
La salida de esta práctica se publicará al ejecutarla con una clave con saldo. El curso no muestra salidas que no hayan salido de una ejecución real.
:::

Al leerla, fíjate en tres cosas:

- **Las preguntas que gana y pierde**, no solo el total. Con 58 preguntas, una diferencia de dos o tres casos puede ser ruido (lección 03 del módulo 4).
- **Las categorías de la lección 06**: si la API arregla las que el modelo local no arreglaba (las inyecciones, las fuentes contradictorias) o solo las que ya arreglaba el de 7B.
- **El coste por cada 1000 preguntas** frente al volumen real que esperas. Un céntimo por pregunta parece poco hasta que lo multiplicas por el tráfico de un mes.

## Claude

Anthropic no usa el formato de OpenAI: tiene su propia API y su SDK oficial. Cómo llamarla está en el [anexo A](../a-claude-y-claude-code/). Integrarla como proveedor de `curso_core` exige un dialecto nuevo en el cliente, igual que existe uno para Ollama. Está pendiente.

## Otros proveedores

Cualquier proveedor con API compatible con OpenAI (Hugging Face Inference Providers, que ya usa el rol `remoto` del módulo 1, vLLM en tu propio servidor, y muchos otros) se configura igual: una sección en `[providers]` con `tipo = "openai"`, su `base_url`, el nombre de la variable de su clave y, si lo pide, `parametro_max_tokens`. Y un rol que lo use.

## Errores frecuentes

**Comparar el modelo de la API con las cifras publicadas en el curso.** Las del curso son con un modelo local concreto. Compara las dos configuraciones sobre los mismos casos, como hace `con_api.py`.

**Olvidar el coste de las evals.** Una eval con juez hace dos llamadas por pregunta, y la iteras muchas veces. Calcula el coste de una ejecución antes de lanzar diez.

**Poner la clave donde no toca.** Solo en `.env`, que está en `.gitignore`. Si una clave acaba en un commit, revócala aunque borres el commit: sigue en el historial.

### Anatomía de un error: la clave que no está

```text
No se puede usar el rol chat_openai: Falta la variable de entorno OPENAI_API_KEY en .env
```

**Cómo leerlo.** El script se para antes de hacer ninguna llamada a OpenAI. El mensaje viene de `curso_core`, no del proveedor: el rol `chat_openai` usa el proveedor `openai`, cuyo `api_key_env` es `OPENAI_API_KEY`, y esa variable está vacía en `.env`.

**Causa.** No se ha copiado la clave en `.env`, o se ha copiado con otro nombre, o el `.env` no está en la raíz del repositorio (`curso_core` lo busca junto a la carpeta `config/`).

**Solución.** Añade la línea `OPENAI_API_KEY=...` a `.env` en la raíz y vuelve a ejecutar. Si después el error es un 401, la clave no es válida. Si es un 429 o un error de cuota, la clave es válida pero la cuenta no tiene saldo o ha superado su límite: lo verás con el `status` y el cuerpo del error en la traza, como en la lección 04 del módulo 1.

## Para profundizar

- [Precios de la API de OpenAI](https://developers.openai.com/api/docs/pricing) y [lista de modelos](https://developers.openai.com/api/docs/models).
- [Referencia de Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), con los parámetros que acepta cada modelo.
- [Precios de la API de Claude](https://platform.claude.com/docs/en/about-claude/pricing).

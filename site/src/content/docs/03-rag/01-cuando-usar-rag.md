---
title: "Cuándo usar RAG (y cuándo no)"
description: "Cuándo usar RAG (y cuándo no)"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el modelo con el que se construyó el curso (Qwen2.5 1.5B Instruct) y el modelo de embeddings bge-m3, en Ollama. Los precios de la comparación son los publicados por la API de Hugging Face en la fecha de revisión.
:::

## Objetivos

Al terminar esta lección podrás:

- Explicar qué problema resuelve RAG y qué alternativas hay.
- Comparar con datos tres estrategias: sin documentación, toda la documentación en el prompt y RAG.
- Decidir cuándo compensa RAG según el tamaño de la documentación, el coste y la calidad.
- Reconocer una alucinación que parece apoyada en el contexto.

## Teoría

### El problema: el modelo no conoce tus datos

Un modelo sabe lo que vio en su entrenamiento. No conoce los runbooks de tu empresa, tus SLA ni el postmortem de la semana pasada. Si le preguntas por ellos, en el mejor caso dice que no lo sabe; en el peor, se inventa algo plausible.

Hay tres formas de darle esa información:

1. **Ponerla en el prompt.** Toda la documentación, en cada llamada. Sencillo, pero limitado por la ventana de contexto (módulo 1) y caro: pagas esos tokens cada vez.
2. **Ajustar el modelo** (fine-tuning) con tus datos. Lo verás en el módulo 7. Es caro, lento de actualizar y no garantiza que el modelo recuerde un dato concreto.
3. **Recuperar y generar** (RAG, *retrieval-augmented generation*). Antes de preguntar al modelo, buscas en tu documentación los fragmentos relevantes para la pregunta y solo pones esos en el prompt.

Si vienes de backend, RAG es una caché de lectura al revés: en lugar de traer al modelo toda la base de datos, haces una consulta y le pasas el resultado.

### Las piezas de un RAG

```text
                 ┌────────── indexación (una vez) ──────────┐
documentos ──▶ trocear ──▶ embeddings ──▶ índice
                                            │
pregunta ──▶ embedding ──▶ buscar los k más parecidos ──▶ prompt con esos fragmentos ──▶ modelo ──▶ respuesta
```

Cada pieza tiene su lección en este módulo: trocear (02), embeddings e índices (03), buscar bien (04), reordenar (05) y generar con citas sin inventar (06).

### El caso de este módulo

La plataforma de los tickets del módulo 2 tiene documentación interna: 29 documentos inventados para el curso (arquitectura, runbooks, SLA, política de guardias, postmortems), en `modulos/03-rag/datos/docs/`. Y 30 preguntas de evaluación, en `datos/preguntas.jsonl`: 26 con respuesta en la documentación y 4 sin ella ("¿cuál es el teléfono de la persona de guardia?"). Para esas 4, la respuesta correcta es decir que no aparece.

Cada pregunta lleva el dato clave que debe contener una respuesta correcta ("200", "587", "99,5"...) y las frases exactas de la documentación que la responden. Así se puede medir sin un juez (el juez llega en la lección 06).

## Práctica

[`cuando_rag.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/03-rag/cuando_rag.py) responde las 30 preguntas con cuatro estrategias:

1. Sin documentación ([`rag/sin-contexto`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/rag/sin-contexto.md)).
2. Toda la documentación en el prompt, con el contexto por defecto de Ollama.
3. Toda la documentación en el prompt, con 8 192 tokens de contexto.
4. Un RAG básico: las 3 secciones más parecidas a la pregunta según bge-m3 ([`rag/con-contexto`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/rag/con-contexto.md)).

Necesitas el modelo de embeddings:

```sh title="Cualquier terminal"
ollama pull bge-m3
```

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/03-rag/cuando_rag.py
```

```text
Índice: 97 secciones en 15.5 s

estrategia                        aciertos abstiene bien  tokens  latencia
1. sin documentación                 2/26         3/4      82     1.36s
2. todo, contexto por defecto        9/26         2/4    2050     8.91s
3. todo, contexto 8192              19/26         3/4    5425     3.75s
4. RAG (top 3 secciones)            17/26         2/4     300     2.29s

Respuesta a '¿Cuál es la disponibilidad comprometida del servicio de notificaciones?':
  [1. sin documentación] 'La disponibilidad comprometida del servicio de notificaciones es de 99,9%.'
  [2. todo, contexto por defecto] 'La disponibilidad comprometida del servicio de notificaciones es de 99,5%.'
  [3. todo, contexto 8192] 'La disponibilidad comprometida del servicio de notificaciones es del 99,5 %.'
  [4. RAG (top 3 secciones)] 'La disponibilidad comprometida del servicio de notificaciones es del 99,5 % mensual.'
```

## Mide y depura

### Leer la tabla

- **Sin documentación**, el modelo acierta 2 de 26. Y en la pregunta del SLA se inventa un 99,9 % con total naturalidad. Por casualidad, es la cifra que aparece en un documento antiguo; la vigente es 99,5 %.
- **Toda la documentación con el contexto por defecto** se queda en 9 de 26. Son unos 5 400 tokens de documentación y el servidor procesa 2 050: recorta en silencio, como viste en la lección 02 del módulo 1.
- **Toda la documentación con contexto suficiente** es lo que más acierta: 19 de 26.
- **RAG** acierta 17 de 26 con **18 veces menos tokens** de entrada por pregunta (300 frente a 5 425).

### El coste de "meterlo todo"

Con un proveedor que cobra 0,01 $ por millón de tokens de entrada (el modelo de 4B de la lección 06 del módulo 1), solo la entrada de un millón de preguntas costaría unos 54 $ metiendo toda la documentación y unos 3 $ con RAG. Con modelos más caros, la diferencia crece en proporción.

En local no pagas por token, pero pagas en tiempo: la primera llamada con toda la documentación tarda alrededor de 45 segundos en procesar la entrada en un equipo sin GPU. La media de 3,75 s es engañosamente baja porque las 29 preguntas siguientes reutilizan la caché del prompt (lección 06 del módulo 1): la documentación va primero y es idéntica en todas. En cuanto cambia un documento, la caché se pierde.

### Cuándo compensa cada estrategia

| Situación | Estrategia |
| --- | --- |
| Pocos documentos, que caben con margen en el contexto, y pocas consultas | Meterlo todo puede ser lo más sencillo y lo que más acierta |
| Documentación que no cabe o que crece | RAG |
| Muchas consultas o un modelo de pago | RAG: el ahorro de tokens se multiplica |
| Necesitas citar de dónde sale cada respuesta | RAG: sabes qué fragmentos usó |
| Información que el modelo ya conoce de forma general | Ninguna: el modelo solo puede bastar |

Fíjate en que esta documentación es pequeña a propósito (29 documentos). En una empresa real hay miles, y "meterlo todo" deja de ser una opción.

### Lo que no mide esta tabla

El RAG falla 9 de 26. ¿Porque no encontró el fragmento correcto, o porque lo encontró y el modelo no lo usó bien? Son dos problemas distintos con soluciones distintas, y separarlos es el trabajo de las lecciones siguientes: medir la recuperación (lección 04) y la generación (lección 06) por separado.

## Errores frecuentes

**Montar un RAG sin probar antes la alternativa sencilla.** Si tu documentación cabe en el contexto, mide primero cuánto acierta metiéndola entera. Aquí acertaba más que el RAG.

**Olvidar el contexto por defecto del servidor.** "Meterlo todo" con el contexto de 4 096 tokens de Ollama dio 9 de 26, peor que el RAG. El fallo no se ve: no hay error, solo respuestas peores.

**Evaluar solo preguntas con respuesta.** Un sistema que responde algo a todo parece mejor de lo que es. Incluye preguntas sin respuesta y mide si se abstiene.

### Anatomía de un error: el servicio que no existe

Pregunta número 28, sin respuesta en la documentación: la plataforma no tiene ningún servicio de recomendaciones.

```text
28 ¿Qué base de datos usa el servicio de recomendaciones?
   -> 'El servicio de recomendaciones utiliza PostgreSQL como base de datos principal.'
   recuperado: ['Arquitectura general de la plataforma > Servicios y equipos (0.47)',
                'Postmortem: productos nuevos sin indexar (mayo de 2026) > Causa raíz (0.43)',
                'Arquitectura del servicio de notificaciones (0.43)']
```

**Cómo leerlo.** La respuesta tiene todo el aspecto de venir de la documentación: es concreta y técnica. Las secciones recuperadas explican de dónde sale. La primera es la tabla de servicios, donde tres de los cinco usan PostgreSQL. El modelo ha completado el patrón con un servicio que no está en la tabla.

**Causa.** El RAG siempre devuelve los k fragmentos más parecidos, aunque ninguno sea relevante. Para el modelo, "aquí hay documentación sobre bases de datos de servicios" se parece mucho a "aquí está la respuesta". El prompt le pide decir "No aparece en la documentación", pero el contexto le da material para no hacerlo.

**Solución.** Dos defensas, que verás más adelante. En la recuperación: fíjate en la puntuación. La mejor coincidencia para esta pregunta es 0,47. En las 26 preguntas con respuesta, la mejor coincidencia va de 0,57 a 0,85 (mediana 0,68); en las 4 sin respuesta, de 0,47 a 0,60. Los rangos se solapan, así que un umbral mínimo ayuda pero no basta: con 0,60, descartarías 2 preguntas que sí tienen respuesta y dejarías pasar una que no. En la generación: pedir citas y comprobar que la respuesta se apoya en ellas (lección 06).

## Para profundizar

- Lewis et al., [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) (2020). El artículo que dio nombre a RAG.
- Liu et al., [Lost in the Middle](https://arxiv.org/abs/2307.03172) (2023). Por qué meter mucho texto en el contexto no garantiza que el modelo lo use.
- [Embeddings en Ollama](https://docs.ollama.com/capabilities/embeddings): el endpoint que usa la práctica.
- [Ficha de bge-m3](https://huggingface.co/BAAI/bge-m3) en Hugging Face.

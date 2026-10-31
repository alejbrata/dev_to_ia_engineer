---
title: "Recuperación"
description: "Recuperación densa, léxica (BM25) e híbrida (RRF): cuándo gana cada una, cómo medirlas y por qué un umbral de similitud no basta"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el modelo de embeddings bge-m3 en Ollama y la implementación de BM25 de `curso_core`. Con otro modelo de embeddings, los números cambian; el método para compararlos, no.
:::

## Objetivos

Al terminar esta lección podrás:

- Implementar y explicar la búsqueda léxica con BM25.
- Combinar búsqueda densa y léxica con Reciprocal Rank Fusion (RRF).
- Medir las tres con recall@k, precision@k y MRR, y leer qué significa cada número.
- Encontrar las consultas en las que una búsqueda gana a la otra y explicar por qué.
- Decidir si un umbral de puntuación te sirve para detectar preguntas sin respuesta.

## Teoría

### Dos formas de buscar

La **búsqueda densa** es la de la lección anterior: compara embeddings. Encuentra textos que dicen lo mismo con otras palabras ("cobros" y "pagos", "precios viejos" y "réplica con retraso"). Su debilidad son los términos que el modelo no ha visto o no distingue bien: identificadores, códigos de error, nombres internos.

La **búsqueda léxica** compara palabras. Es la de los buscadores de toda la vida: Lucene, Elasticsearch, OpenSearch, la búsqueda de texto completo de PostgreSQL. Si buscas `perfil_edicion`, encuentra los fragmentos que contienen `perfil_edicion`. No sabe que "cobros" y "pagos" son lo mismo.

### BM25

BM25 es la puntuación léxica estándar. Para cada palabra de la consulta que aparece en un fragmento, suma una cantidad que depende de tres cosas:

- **Lo rara que es la palabra** en el corpus (IDF, *inverse document frequency*). "pagos" aparece en muchos fragmentos y aporta poco; `OPENSEARCH_URL` aparece en dos y aporta mucho.
- **Cuántas veces aparece** en el fragmento, con rendimientos decrecientes: la décima repetición suma menos que la segunda (parámetro `k1`).
- **La longitud del fragmento**: un fragmento largo contiene más palabras por pura estadística, así que se le penaliza un poco (parámetro `b`).

`curso_core.rag.IndiceLexico` lo implementa en menos de 50 líneas, con los valores habituales `k1 = 1,5` y `b = 0,75`. Antes de contar, pasa el texto a minúsculas, quita las tildes y descarta palabras vacías ("de", "la", "que"…). No hace *stemming* (reducir "conexiones" a "conexion"): es una mejora habitual que aquí no hace falta para ver las diferencias.

Una propiedad útil: si ninguna palabra coincide, BM25 no devuelve nada. La búsqueda densa siempre devuelve k resultados, aunque no se parezcan a la pregunta.

### Búsqueda híbrida y RRF

La idea es obvia: buscar de las dos formas y combinar. El problema es cómo. Las puntuaciones no son comparables: el coseno va de -1 a 1 y BM25 no tiene techo (en este corpus, de 0 a 22). Sumarlas no tiene sentido.

**Reciprocal Rank Fusion** combina posiciones, no puntuaciones. Cada fragmento suma `1 / (60 + posición)` por cada lista en la que aparece. Un fragmento que sale tercero en las dos listas suma más que uno que sale primero en una y no aparece en la otra. El 60 es el valor del paper original; amortigua la ventaja de los primeros puestos. `IndiceHibrido` pide 20 candidatos a cada búsqueda y los fusiona con `fusion_rrf`.

### Qué mide cada métrica

Las tres se calculan sobre las 26 preguntas con respuesta, con los k primeros resultados de cada una:

- **recall@k**: fracción de preguntas con al menos un fragmento relevante entre los k primeros. ¿Llega la respuesta al modelo?
- **precision@k**: fracción media de los k primeros que son relevantes. ¿Cuánto ruido acompaña a la respuesta?
- **MRR**: media de 1/posición del primer relevante, con los 3 primeros. ¿Sale la respuesta arriba?

La precisión tiene un techo que hay que conocer antes de leerla. En este corpus, 21 preguntas tienen un solo fragmento relevante y 5 tienen dos. Con k = 3, la precisión máxima posible es del 40 %: aunque la búsqueda fuera perfecta, al menos dos de cada tres fragmentos recuperados no tendrían la respuesta.

## Práctica

[`recuperacion.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/03-rag/recuperacion.py) indexa las secciones de las tres formas y las mide con las mismas preguntas:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/03-rag/recuperacion.py
```

```text
1. Recuperación, 26 preguntas con respuesta
   búsqueda         recall@1  recall@3  recall@5  precision@3   MRR  ms/búsqueda
   densa (bge-m3)       62%       85%       96%          32%  0.72         90.3
   léxica (BM25)        46%       81%       85%          29%  0.61          0.3
   híbrida (RRF)        58%       85%       88%          31%  0.71         89.1

2. Aciertos en el top 3 que solo consigue una de las dos
   solo densa    5. La base de datos de cobros ha dejado de aceptar conexiones nuevas. ¿Qué procedimiento sigo?
   solo léxica  11. ¿Cuál fue la causa de la caída de pagos de marzo de 2026?
   solo densa   15. La tienda está enseñando precios viejos. ¿Qué hago?

3. Puntuación del primer resultado: con respuesta frente a sin respuesta
   densa (bge-m3)   con respuesta  0.570 a  0.850 · sin respuesta  0.466 a  0.596
   léxica (BM25)    con respuesta  6.832 a 21.861 · sin respuesta  7.216 a  9.977
   híbrida (RRF)    con respuesta  0.032 a  0.033 · sin respuesta  0.031 a  0.033
   Umbral sobre la similitud densa del primer resultado:
   0.55: descarta 0 de 26 con respuesta, deja pasar 2 de 4 sin respuesta
   0.60: descarta 2 de 26 con respuesta, deja pasar 0 de 4 sin respuesta
   0.65: descarta 8 de 26 con respuesta, deja pasar 0 de 4 sin respuesta

4. Consultas con un identificador, como las que se pegan desde un log
   invalid_grant
     densa (bge-m3)   runbook-usuarios-google#1     0.639  (contiene el identificador · resultados: 3)
     léxica (BM25)    runbook-usuarios-google#0     4.468  (contiene el identificador · resultados: 2)
     híbrida (RRF)    runbook-usuarios-google#1     0.033  (contiene el identificador · resultados: 3)
   OPENSEARCH_URL
     densa (bge-m3)   arquitectura-busqueda#3       0.644  (contiene el identificador · resultados: 3)
     léxica (BM25)    arquitectura-busqueda#3       4.252  (contiene el identificador · resultados: 2)
     híbrida (RRF)    arquitectura-busqueda#3       0.033  (contiene el identificador · resultados: 3)
   precios_desde_principal
     densa (bge-m3)   runbook-catalogo-replica#2    0.479  (contiene el identificador · resultados: 3)
     léxica (BM25)    runbook-catalogo-replica#2    3.686  (contiene el identificador · resultados: 1)
     híbrida (RRF)    runbook-catalogo-replica#2    0.033  (contiene el identificador · resultados: 3)
   perfil_edicion
     densa (bge-m3)   arquitectura-usuarios#2       0.439  (NO contiene el identificador · resultados: 3)
     léxica (BM25)    runbook-usuarios-deadlocks#2  3.555  (contiene el identificador · resultados: 1)
     híbrida (RRF)    runbook-usuarios-deadlocks#2  0.033  (contiene el identificador · resultados: 3)
```

## Mide y depura

### Con estas preguntas, la híbrida no mejora a la densa

Es el resultado, y hay que decirlo: con las 26 preguntas de evaluación, la búsqueda densa es la mejor en todas las métricas. La híbrida empata en recall@3 y queda por detrás en recall@1, recall@5 y MRR. La léxica es la peor, pero tarda 0,3 ms frente a 90.

No es que la híbrida sea mala. Es que las preguntas de evaluación están escritas en lenguaje natural, con paráfrasis ("cobros" por "pagos", "precios viejos" por "réplica con retraso"), y ese es el terreno de la búsqueda densa. Al fusionar, BM25 cuela candidatos que solo comparten palabras sueltas y desplaza alguno bueno de los primeros puestos.

### Con identificadores, la densa falla

La parte 4 prueba otro tipo de consulta: un identificador suelto, como el que alguien copia de un log o de una alerta. Aquí cambia el reparto:

- Con `perfil_edicion`, la búsqueda densa devuelve primero una sección de arquitectura que no lo menciona. BM25 devuelve un único resultado, el correcto.
- Con `precios_desde_principal`, la densa acierta, pero con una similitud de 0,479. Cualquier umbral de los de la parte 3 lo descartaría como "sin respuesta".
- La híbrida acierta en las cuatro.

Ninguna búsqueda es mejor en abstracto. Depende de qué preguntan tus usuarios. Por eso las preguntas de evaluación tienen que parecerse a las reales: si tu evaluación solo tiene preguntas bien redactadas y tus usuarios pegan códigos de error, medirás una cosa y desplegarás otra. Si tienes los dos tipos, mídelos por separado.

### Por qué falla cada una

Mira los desacuerdos de la parte 2 con los fragmentos delante:

- **Pregunta 5** ("La base de datos de cobros ha dejado de aceptar conexiones nuevas"). La respuesta está en la sección de mitigación del runbook de *pagos*. BM25 no sabe que cobros y pagos son lo mismo, y "procedimiento" o "sigo" no aparecen en la sección buena. La densa la pone segunda.
- **Pregunta 11** ("¿Cuál fue la causa de la caída de pagos de marzo de 2026?"). La sección buena se titula `Causa raíz`. BM25 cuenta "causa" y la pone segunda; la densa no la incluye en sus tres primeros, aunque los tres son del postmortem correcto.
- **Pregunta 15** ("La tienda está enseñando precios viejos"). La respuesta habla de la réplica del catálogo y de su retraso. Ni "tienda" ni "viejos" aparecen. Solo la densa la encuentra, y tercera.

### Un umbral no separa las preguntas sin respuesta

Si el primer resultado se parece poco a la pregunta, quizá la documentación no tenga la respuesta. La parte 3 lo pone a prueba con las 4 preguntas sin respuesta:

- En la densa, los rangos se solapan: con respuesta, de 0,570 a 0,850; sin respuesta, de 0,466 a 0,596. Con 0,60 no se cuela ninguna sin respuesta, pero descartas 2 que sí la tienen. Y la parte 4 añade otro problema: las consultas con identificadores puntúan por debajo de 0,5 aunque el resultado sea correcto.
- En BM25, las preguntas sin respuesta puntúan como las que sí la tienen: comparten palabras comunes con muchos fragmentos.
- En RRF, la puntuación no sirve para esto: depende solo de las posiciones, y el primer resultado siempre ronda 1/61 + 1/61.

Un umbral sirve como señal (en trazas, en un panel, para revisar a mano), no como decisión. Para decidir si hay respuesta, hay que mirar la respuesta generada: lo harás en la lección 06.

### Qué métrica mirar

- **recall@k con el k que usas en el prompt.** Si metes 3 fragmentos, recall@3. Un recall@5 alto no ayuda si solo metes 3.
- **recall@1 y MRR** si el orden importa: los modelos no aprovechan igual toda la información del contexto (Liu et al., *Lost in the Middle*, en "Para profundizar"). Lo que va primero tiene más papeletas de usarse.
- **precision@k** con su techo al lado. Un 32 % sobre un máximo del 40 % es bueno.
- **Latencia**, separando el embedding de la búsqueda. Aquí, la búsqueda híbrida cuesta lo mismo que la densa: el tiempo se va en el embedding de la pregunta, no en BM25.

## Errores frecuentes

**Dar por hecho que la híbrida siempre gana.** Es la recomendación habitual, y con frecuencia es buena. Pero en este corpus y con estas preguntas, empeora el orden. Mide con tus preguntas antes de añadir complejidad.

**Evaluar solo con preguntas bien redactadas.** Si en producción llegan identificadores, códigos de error o nombres de servicios sueltos, inclúyelos en la evaluación.

**Comparar puntuaciones de búsquedas distintas.** Un 4,4 de BM25 y un 0,64 de coseno no se pueden sumar ni comparar. Para combinar, usa posiciones (RRF) o normaliza cada lista antes.

**Olvidar las palabras vacías o las tildes.** Sin normalizar, "búsqueda" y "busqueda" son palabras distintas, y "de" puntúa en todos los fragmentos.

### Anatomía de un error: el identificador que la búsqueda densa no encuentra

Alguien pega en el asistente el nombre de una tabla que aparece en un error de la base de datos:

```text
perfil_edicion
  densa (bge-m3)   arquitectura-usuarios#2       0.439  (NO contiene el identificador · resultados: 3)
  léxica (BM25)    runbook-usuarios-deadlocks#2  3.555  (contiene el identificador · resultados: 1)
```

**Cómo leerlo.** La búsqueda densa devuelve tres resultados, como siempre, y el primero es una sección sobre la arquitectura del servicio de usuarios. Parece razonable: el tema es parecido. Pero no menciona `perfil_edicion`, y la similitud, 0,439, está por debajo de la de cualquier pregunta con respuesta del conjunto de evaluación. BM25 devuelve un único resultado: el runbook de *deadlocks*, que es el que habla de esa tabla.

**Causa.** El tokenizador de bge-m3 parte `perfil_edicion` en cuatro tokens: `▁perfil`, `_`, `edici` y `on`. El vector que sale de ahí representa algo como "perfil, edición": un tema, no un nombre que haya que encontrar literalmente. Y de perfiles habla también la sección de arquitectura. BM25 no entiende nada, pero tampoco lo necesita: la palabra aparece en un único fragmento, así que su IDF es máximo.

**Solución.** Si tus usuarios buscan identificadores, añade búsqueda léxica: como búsqueda híbrida, o como una ruta aparte cuando la consulta parece un identificador. Y añade esas consultas a tu evaluación, porque las preguntas en lenguaje natural no lo detectan: con ellas, la híbrida parecía peor.

## Para profundizar

- Robertson y Zaragoza, [The Probabilistic Relevance Framework: BM25 and Beyond](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf) (2009). La referencia de BM25.
- Cormack, Clarke y Büttcher, [Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) (2009). El paper de RRF.
- Thakur et al., [BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663) (2021). Compara BM25 y búsqueda densa en muchos tipos de corpus; BM25 sigue siendo una referencia difícil de batir en varios.
- Liu et al., [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) (2023). Por qué importa en qué posición del contexto queda la respuesta.
- [Búsqueda de texto completo en PostgreSQL](https://www.postgresql.org/docs/current/textsearch.html), si quieres la búsqueda léxica en la misma base de datos que pgvector.

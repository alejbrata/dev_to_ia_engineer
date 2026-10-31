---
title: "Evals de RAG"
description: "Evals de RAG: medir la recuperación y la generación por separado, clasificar cada fallo según la etapa en la que se pierde y no atribuir a una etapa lo que hace la otra"
---

:::note[Revisado: 2026-10]
Las salidas son reales. El sistema es el RAG de las lecciones anteriores: bge-m3 para la búsqueda, el reranker bge-reranker-v2-m3 en `llama-server` y Qwen2.5 1.5B Instruct para generar. El juez es Qwen2.5 7B Instruct (rol `judge`). Todo sobre CPU.
:::

## Objetivos

Al terminar esta lección podrás:

- Medir por separado si el dato llega al contexto (recuperación) y si el modelo lo usa bien (generación), con el mismo dataset anclado.
- Clasificar cada fallo según la etapa en la que se pierde.
- Reconocer cuándo mejorar la recuperación ya no mejora el sistema, porque el cuello de botella se ha movido a la generación.
- Distinguir fidelidad y corrección, y combinar el comprobador de datos clave con el juez.

## Teoría

### Una cifra final mezcla dos fallos

Un RAG tiene dos etapas, y cualquiera de ellas puede estropear la respuesta. Si el fragmento con el dato no llega al contexto, el modelo no puede responder bien (o lo hace por casualidad). Si llega y el modelo lo ignora, lo malinterpreta o se abstiene, el fallo es de la generación. "28 de 42" no dice cuál de las dos pasa, y la solución de cada una es distinta: para la recuperación, el chunking, la búsqueda, el reranker o el número de fragmentos (*k*); para la generación, el prompt o el modelo.

Es lo mismo que depurar una petición lenta en un backend. El tiempo total no te dice nada; la traza por tramos (base de datos, llamada externa, serialización) te dice dónde mirar.

### Medir cada etapa con el mismo dataset

Para separar las etapas no hace falta otro dataset. El de la lección 02 ya tiene lo necesario, porque cada pregunta está anclada a segmentos literales del corpus:

- **Recuperación**: ¿alguno de los fragmentos del contexto contiene un segmento de la pregunta? Es el recall de la lección 04 del módulo 3, pero comprobado contra el segmento anclado (`dataset.relevante`), no contra un identificador de fragmento. Como se compara el texto, el dataset sigue sirviendo si cambias el chunking.
- **Corrección**: ¿la respuesta contiene los datos clave? Es el comprobador de la lección 03.
- **Fidelidad**: ¿lo que dice la respuesta está en el contexto? Es el juez v2 de la lección 04.

Cruzando las dos primeras, cada pregunta con respuesta cae en una casilla:

| | La respuesta es correcta | La respuesta falla |
| --- | --- | --- |
| **El segmento llega al contexto** | correcta | fallo de generación (se abstiene o responde mal con el dato delante) |
| **El segmento no llega** | correcta sin el segmento: revisa el anclaje o el comprobador | fallo de recuperación (se abstiene o responde sin el dato) |

La casilla "correcta sin el segmento" no debería existir. Si aparece, o el dato está en otro sitio del corpus que el dataset no ancló, o el comprobador acepta algo que no debería. En la primera ejecución de esta práctica apareció una vez: la n-15 con reranker-k3. El dato ("5 minutos") estaba también en el runbook de la réplica del catálogo ("A partir de 5 minutos salta una alerta."), y el dataset solo anclaba la tabla de alertas. Se añadió ese segundo segmento y la casilla quedó a cero. Para eso sirve: para encontrar anclajes incompletos.

La fidelidad añade otra dimensión. Una respuesta puede ser **fiel e incorrecta**, si el contexto que recibió era el equivocado. Y puede ser **correcta y no fiel**, si acierta el dato pero inventa lo que lo rodea. Por eso se miden las dos.

Las librerías de evals de RAG ponen nombre a estas métricas: *context recall* (el dato llega), *context precision* (cuánto de lo que llega sirve), *faithfulness* (fidelidad) y *answer correctness* o *answer relevancy* (la respuesta responde a lo que se preguntó). Aquí se calculan con el código de las lecciones anteriores; el [anexo F](../../anexos/f-herramientas-de-evals/) compara cómo lo hacen esas librerías. La *context precision* no se mide en esta lección.

## Práctica

La práctica compara tres configuraciones del sistema: la búsqueda densa con 3 fragmentos (la de las lecciones anteriores), la densa con reranker y 3 fragmentos, y con reranker y 5 fragmentos. Necesita el reranker de la lección 05 del módulo 3 en marcha:

```sh title="Terminal aparte · se queda en marcha"
llama-server -hf gpustack/bge-reranker-v2-m3-GGUF:Q8_0 --reranking --port 8082
```

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/por_etapas.py
```

[`por_etapas.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/por_etapas.py) responde las 58 preguntas con cada configuración y pasa el juez v2 por las respuestas que no se abstienen. Son unas 320 llamadas a modelos y, en la máquina del curso, alrededor de una hora. Guarda los resultados caso a caso en `resultados/etapas-*.jsonl`; con `--grabadas` los reutiliza sin llamar a nada. La salida:

```text
1. Embudo de las 42 preguntas con respuesta
                                                       densa-k3   reranker-k3   reranker-k5
   el segmento llega al contexto                             37            40            42
   correcta                                                  28            33            33
   correcta sin el segmento                                   0             0             0
   recuperación: se abstiene                                  0             0             0
   recuperación: responde sin el dato                         5             2             0
   generación: se abstiene con el dato delante                2             2             2
   generación: responde mal con el dato delante               7             5             7

2. Fidelidad (juez v2) y preguntas que no deben responderse
   densa-k3     fieles 37 de 47 que contestan · no deben responderse:  9 de 16 bien
   reranker-k3  fieles 36 de 47 que contestan · no deben responderse:  9 de 16 bien
   reranker-k5  fieles 39 de 48 que contestan · no deben responderse:  8 de 16 bien

3. Aciertos con respuesta, intervalo y comparación caso a caso
   densa-k3     28 de 42  [ 52%,  79%]
   reranker-k3  33 de 42  [ 64%,  88%]
   reranker-k5  33 de 42  [ 64%,  88%]
   densa-k3 → reranker-k3: gana ['m3-11', 'm3-19', 'm3-21', 'm3-24', 'm3-26', 'n-07', 'n-15'], pierde ['m3-15', 'n-04'], p = 0.18
   reranker-k3 → reranker-k5: gana ['m3-01', 'm3-15'], pierde ['m3-26', 'n-05'], p = 1.00
```

La configuración densa-k3 da 28 de 42, lo mismo que en la lección 02: es el mismo sistema con el mismo dataset.

## Mide y depura

### El embudo: el cuello de botella se mueve

Con la búsqueda densa, el segmento llega al contexto en 37 de las 42 preguntas, y el sistema acierta 28. De los 14 fallos, 5 son de recuperación y 9 de generación. El reranker baja los de recuperación a 2, y con 5 fragmentos a 0: el segmento llega siempre.

Pero los aciertos se quedan en 33. Con reranker-k5 los 9 fallos que quedan son de generación: el modelo tiene el dato delante y se abstiene (2) o responde otra cosa (7). A partir de aquí, seguir mejorando la recuperación no mejora el sistema. La siguiente palanca es la generación, y es lo que trata la lección 06.

Sin el desglose por etapas, el salto de k3 a k5 parecería simplemente "no sirve". Con él se ve qué pasa: la recuperación mejora (40 → 42) y la generación empeora (5 → 7 respuestas mal con el dato delante). Las dos cosas se compensan.

### Más contexto no es gratis

De k3 a k5, el sistema gana dos preguntas (m3-01 y m3-15, cuyo segmento ahora sí llega) y pierde otras dos que antes acertaba (m3-26 y n-05). En la n-05, el modelo tiene la tabla correcta delante y lee la fila equivocada (es la anatomía de abajo). También responde una pregunta que debía rechazar: en la s-02 afirma que "El clúster de OpenSearch tiene 3 nodos", un dato que no está en ningún sitio. Con más fragmentos hay más distractores, y un modelo de 1,5B se confunde más.

Además, cada fragmento de más son tokens de más en cada llamada. En tus trazas, compara los tokens de entrada y la latencia de generación con k3 y con k5 antes de subir *k* "por si acaso".

### No atribuyas a una etapa lo que hace la otra

El reranker gana 7 preguntas y pierde 2. Parece que todas las ganancias son mérito de la recuperación, pero el desglose dice otra cosa. Solo 3 de las 7 (m3-11, m3-19 y m3-24) eran fallos de recuperación que el reranker arregla, y son justo las tres preguntas que la lección 05 del módulo 3 vio subir desde fuera del top 3. Las otras 4 (m3-21, m3-26, n-07 y n-15) ya tenían el segmento delante con la búsqueda densa y fallaban en la generación: con el reranker, el contexto cambia de orden y de compañía, y el modelo acierta. Y de las 2 que pierde, la n-04 tiene el segmento en las dos configuraciones.

Es decir, el generador es sensible a qué fragmentos le llegan y en qué orden, aunque el dato esté. Parte de la diferencia entre configuraciones es esa sensibilidad, no la calidad de la recuperación.

### ¿Es real la mejora?

33 de 42 frente a 28 de 42 son 5 aciertos más, pero los intervalos se solapan ([52 %, 79 %] y [64 %, 88 %]), y la prueba de McNemar sobre los casos que cambian (7 ganados, 2 perdidos) da p = 0,18. Con 42 preguntas, no basta para afirmar que el reranker mejora las respuestas.

Eso no significa que no mejore. La lección 05 del módulo 3 midió que el reranker sube el recall@3 en la recuperación aislada, y aquí los fallos de recuperación bajan de 5 a 2: hay un mecanismo y va en la dirección esperada. Lo que no hay son datos suficientes para dar una cifra de mejora de las respuestas. Para eso hacen falta más preguntas, no más ejecuciones de las mismas.

### Fidelidad no es corrección

Según el juez v2, de las respuestas que no se abstienen son fieles 37 de 47 (densa-k3), 36 de 47 (reranker-k3) y 39 de 48 (reranker-k5). Recuerda lo que se midió en la lección 04: este juez detecta el 83 % de las respuestas no fieles y, cuando da la alarma, casi siempre acierta. Las cifras sirven para comparar, no como fidelidad exacta.

Lo útil es cruzar la fidelidad con la corrección caso a caso:

- **Fiel e incorrecta.** En la n-06 con la búsqueda densa, el sistema responde que la disponibilidad de notificaciones es "del 99,9 % mensual". El SLA vigente (99,5 %) no llegó al contexto, y el 99,9 % sí está en lo que recibió. La respuesta es fiel a su contexto y falsa. Es un fallo de recuperación, y el juez no lo puede ver.
- **Correcta y no fiel, según el juez.** En la n-15 con reranker-k3, la respuesta contiene el dato clave ("5 minutos") y el comprobador la da por buena. El juez la marca como no fiel, pero por una razón discutible: la frase sin cita es la introducción ("sigue estos pasos:"), que no afirma nada. Es un tipo de falsa alarma del juez que conviene conocer.
- **Sin respuesta.** Las preguntas que no deben responderse se quedan en 9 de 16 con las dos primeras configuraciones y bajan a 8 con k5. La recuperación no las arregla: el modelo responde a lo que no está, sigue la inyección del guardarraíl o contesta fuera de ámbito tenga el contexto que tenga. En la s-02, el juez sí detecta la invención (la afirmación de los 3 nodos no tiene cita).

## Errores frecuentes

**Mirar solo la cifra final.** "28 de 42" no dice si el problema está en la búsqueda o en el modelo. Sin el desglose, puedes pasarte una semana afinando el chunking cuando el dato ya llega y es el modelo el que falla.

**Seguir mejorando la etapa que ya no limita.** Cuando los fallos de recuperación llegan a cero, mejorar la búsqueda no sube los aciertos. Mira el embudo antes de decidir dónde invertir.

**Atribuir toda la mejora al componente que cambiaste.** Un cambio en la recuperación también cambia el contexto que ve el generador, y eso altera respuestas que no tenían ningún problema de recuperación. Clasifica los casos ganados y perdidos por etapa antes de explicar la mejora.

**Subir *k* por si acaso.** Más fragmentos suben el recall y también los distractores, los tokens y la latencia. Con un modelo pequeño, puede no compensar.

**Confundir fidelidad con corrección.** Un juez de fidelidad aprueba una respuesta fiel a un contexto equivocado. La corrección se mide con los datos clave del dataset; la fidelidad, con el juez. Hacen falta las dos.

### Anatomía de un error: más contexto, peor respuesta, y el juez la aprueba

```text
n-05 ¿Qué disponibilidad tenemos comprometida para el servicio de búsqueda?
  reranker-k3  recuperados: sla#1, arquitectura-notificaciones#2, arquitectura-busqueda#0
               respuesta:   'El servicio de búsqueda tiene una disponibilidad comprometida del 99,5 % mensual.'
  reranker-k5  recuperados: sla#1, arquitectura-notificaciones#2, arquitectura-busqueda#0,
                            arquitectura-busqueda#3, sla#2
               respuesta:   'El servicio de búsqueda tiene una disponibilidad del 99,95 % mensual.'
               juez v2:     fiel · cita: 'pagos | 99,95 % |'
```

**Cómo leerlo.** En las dos configuraciones, el primer fragmento es `sla#1`, la tabla de disponibilidad, que contiene el segmento anclado (`| busqueda | 99,5 % |`). La recuperación es perfecta en los dos casos. Con k5 llegan dos fragmentos más, uno sobre el despliegue de la búsqueda y otro con la tabla de tiempos de respuesta del SLA, y el modelo responde con el 99,95 % de la fila de pagos. El juez v2 da la respuesta por fiel: copió una cita, el código comprobó que existe, y existe.

**Causa.** Es un fallo de generación: el dato estaba delante y el modelo leyó la fila equivocada. Con más texto en el contexto, el modelo pequeño confunde más las filas de la tabla. El juez no lo detecta por el fallo que ya viste en la lección 04: la cita existe, pero no apoya la afirmación. Es de otra fila. Solo lo detecta el comprobador de datos clave, porque el dataset dice qué dato tiene que aparecer.

**Solución.** Para la generación, hay varias opciones, y cada una se mide con el mismo dataset: quedarse en k3, usar un modelo más capaz o, ya en la ingesta, convertir cada fila de la tabla en una frase completa ("La disponibilidad comprometida de búsqueda es del 99,5 % mensual") para que el modelo no tenga que cruzar filas y columnas. Para la evaluación, no sustituyas el comprobador por el juez: cada uno detecta fallos que el otro no ve.

## Para profundizar

- Es et al., [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217) (2023). Las métricas de contexto, fidelidad y relevancia, separadas por etapa.
- Saad-Falcon et al., [ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems](https://arxiv.org/abs/2311.09476) (2023). Jueces entrenados por etapa, con intervalos de confianza.
- Liu et al., [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) (2023). Cómo cambia el uso del contexto según la posición del dato y la cantidad de texto.
- Barnett et al., [Seven Failure Points When Engineering a Retrieval Augmented Generation System](https://arxiv.org/abs/2401.05856) (2024). Una clasificación de los fallos de un RAG por etapa.

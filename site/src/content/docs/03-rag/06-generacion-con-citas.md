---
title: "Generación con citas y control de alucinaciones"
description: "Pedir respuestas con citas, abstenerse cuando no hay respuesta, y medir fidelidad y relevancia: con comprobaciones deterministas y con un modelo juez, que también hay que comprobar"
---

:::note[Revisado: 2026-10]
Las salidas son reales. Genera Qwen2.5 1.5B Instruct, el modelo con el que se construyó el curso; juzga Qwen2.5 7B Instruct (rol `judge`); el contexto sale de bge-m3 con el reranker de la lección 05. Con otros modelos, los números cambian. Incluso con los mismos, puede variar alguna respuesta entre ejecuciones (módulo 1).
:::

## Objetivos

Al terminar esta lección podrás:

- Pedir respuestas con citas a los fragmentos del contexto y comprobar esas citas con código.
- Medir acierto, abstención y abstención indebida con comprobaciones deterministas.
- Montar un juez de fidelidad (*faithfulness*) y de relevancia (*answer relevancy*) con un modelo local.
- Calibrar un juez antes de fiarte de él, y detectar uno que suspende de más.

## Teoría

### Qué puede fallar después de recuperar

Las lecciones anteriores midieron la recuperación: si la respuesta llega al contexto. Con el reranker, llega en el 92 % de las preguntas. Pero que llegue no garantiza que el modelo la use bien. Hay cuatro fallos típicos en la generación:

- **Inventa.** Añade datos que no están en el contexto, o los mezcla mal. Es la **alucinación**.
- **No se abstiene.** La documentación no tiene la respuesta y el modelo contesta igualmente.
- **Se abstiene sin razón.** La respuesta está en el contexto y el modelo dice que no la encuentra.
- **No responde a lo que se pregunta.** Dice cosas ciertas, pero de otra cosa.

### Cuatro métricas con nombre propio

Estas son las métricas que verás en herramientas como Ragas o DeepEval. Las dos primeras ya las tienes; las otras dos son de la respuesta:

| Métrica | Pregunta que responde | Cómo se mide aquí |
| --- | --- | --- |
| Recall del contexto | ¿Llegó la respuesta al contexto? | recall@3 con las evidencias (lecciones 02-05) |
| Precisión del contexto | ¿Cuánto ruido la acompaña? | precision@3 (lección 04) |
| Fidelidad (*faithfulness*) | ¿Todo lo que dice está en el contexto? | un modelo juez |
| Relevancia de la respuesta (*answer relevancy*) | ¿Responde a la pregunta? | un modelo juez |

Las herramientas las calculan de formas más elaboradas (Ragas, por ejemplo, descompone la respuesta en afirmaciones y comprueba cada una). La idea es la misma, y aquí la construyes tú para ver dónde falla.

### Citas

Pedir citas tiene dos ventajas. Para quien lee, puede ir al documento y comprobarlo. Para ti, una cita es algo que **se comprueba con código**: si el modelo cita el fragmento 2, puedes mirar si el fragmento 2 contiene la evidencia de la pregunta. Es una medida parcial de fidelidad que no necesita ningún juez.

El prompt [`rag/con-citas`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/rag/con-citas.md) numera los fragmentos (`[1]`, `[2]`, `[3]`) y pide un JSON con la respuesta y los números citados. Con `cliente.extraer` y un modelo Pydantic, el formato está garantizado (módulo 2):

```python
class RespuestaCitada(BaseModel):
    respuesta: str
    citas: list[int]
```

### El modelo como juez

La fidelidad no se puede medir con una búsqueda de texto: el modelo parafrasea. La alternativa habitual es pedírselo a otro modelo, normalmente más grande: el patrón **LLM-as-judge**. Aquí el juez es Qwen2.5 7B, cinco veces más grande que el que genera, con dos prompts:

- [`rag/juez-fidelidad`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/rag/juez-fidelidad.md): primero enumera las afirmaciones sin apoyo en el contexto y después da el veredicto. Pedir la lista antes del veredicto obliga al juez a justificarlo.
- [`rag/juez-relevancia`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/rag/juez-relevancia.md): una frase de motivo y si responde o no.

Un juez es un modelo, con todo lo que has visto en el curso: se equivoca, depende del prompt y tiene sesgos. Antes de usar sus números hay que **calibrarlo**: darle casos cuya respuesta conoces y ver cuánto acierta. La práctica empieza por ahí.

## Práctica

Necesitas el modelo juez y el reranker de la lección 05 en marcha:

```sh title="Terminal de VS Code · raíz del repo"
ollama pull qwen2.5:7b
uv run python modulos/03-rag/generacion.py
```

Sin el reranker, añade `--sin-reranker` (el contexto será peor y los números, distintos). Tarda: el juez hace unas 140 llamadas de unos 11 segundos cada una en la máquina del curso, unos 25 minutos en total.

[`generacion.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/03-rag/generacion.py) hace cuatro cosas:

1. **Calibra el juez de fidelidad.** Le pasa las respuestas de referencia de las 13 preguntas cuyo dato clave es un número (fieles, porque salen de la documentación), y las mismas con el número cambiado (no fieles).
2. Genera las respuestas de las 30 preguntas con dos prompts sobre el mismo contexto: texto libre (`rag/con-contexto`, el de la lección 01) y JSON con citas (`rag/con-citas`).
3. Mide cada prompt con comprobaciones deterministas y con el juez.
4. Enseña las respuestas que el juez marca como no fieles.

```text
1. Calibración del juez con las respuestas de referencia
   referencia, tal cual:      fiel en 9 de 13
   referencia con otro dato:  no fiel en 13 de 13
   (con el contexto recuperado: si no trae la respuesta, la referencia no está apoyada)

2 y 3. Dos prompts, el mismo contexto
   rag/con-contexto
     correctas                              20 de 26
     se abstiene bien                        3 de 4
     se abstiene sin razón                   2 de 26
     fieles (juez), de las que contestan    14 de 25
     responden (juez)                       16 de 26
   rag/con-citas
     correctas                              22 de 26
     se abstiene bien                        3 de 4
     se abstiene sin razón                   1 de 26
     fieles (juez), de las que contestan    16 de 26
     responden (juez)                       16 de 26
     JSON válido                            30 de 30
     citan algo, de las que contestan       26 de 26
     citan el fragmento con la evidencia    20 de 26
```

La parte 4 es larga: 22 respuestas con lo que el juez considera sin apoyo. Las más útiles están en "Mide y depura".

## Mide y depura

### Lo determinista: las citas ayudan

Con el mismo contexto, el prompt con citas acierta más (22 de 26 frente a 20) y se abstiene sin razón menos (1 frente a 2). Las dos versiones se abstienen bien en 3 de las 4 preguntas sin respuesta. El JSON es válido siempre: es el esquema del módulo 2 haciendo su trabajo.

Las citas añaden una comprobación que el texto libre no permite: en 20 de 26 respuestas, el modelo cita el fragmento que contiene la evidencia. En las otras 6 cita algo, pero no el fragmento con el dato. Eso no prueba que se haya inventado la respuesta, pero es una señal barata para revisar primero esas.

Respecto a la lección 01 (RAG básico con 3 secciones: 17 de 26), pasar a una recuperación con reranking y a un prompt con citas lleva el acierto a 22 de 26.

### El juez: antes de mirar sus números, mira la calibración

La calibración dice dos cosas:

- Detecta **todas** las respuestas con el dato cambiado (13 de 13). Bien.
- Pero rechaza **4 de las 13 respuestas de referencia**, que son fieles. Las 13 tienen su evidencia en el contexto recuperado; lo puedes comprobar con `corpus.es_relevante` sobre los fragmentos de cada una. El juez se equivoca en el 31 % de las respuestas correctas.

Un juez que suspende de más también detecta todas las trampas. Por eso la calibración necesita las dos mitades: casos que deben aprobar y casos que deben suspender. Con solo la mitad de las trampas, este juez parecería perfecto.

### Revisa a mano lo que marca el juez

El juez dice que solo 16 de 26 respuestas con citas son fieles. Revisando a mano las 22 que marca como no fieles, con la documentación delante:

- **Invenciones reales, con texto libre (4).** En la 5 dice que mantengas el pool en 200 "ya que es el máximo permitido por PostgreSQL"; el runbook dice que el máximo es 250. En la 15 añade que atención al cliente "se comunique con la plataforma de base de datos", que no está en ninguna parte. En la 26 contesta "Sí, debe avisar", cuando la norma es avisar en las medias solo si generan consultas. En la 30 responde "El responsable del equipo Cobros es el responsable del equipo Cobros" en vez de abstenerse.
- **Invenciones reales, con citas (1, y 2 discutibles).** La 30 de nuevo: "El responsable del equipo Cobros es el equipo de Cobros". Discutibles: la 11 traduce "too many connections" como "demasiadas solicitudes", y la 15 inventa para qué se avisa a atención al cliente.
- **Errores del juez (el resto).** Marca como sin apoyo frases que están en el contexto palabra por palabra. Por ejemplo, en la 26 con citas: "Avisa siempre en las incidencias críticas y altas que afecten a clientes. En las medias, solo si generan consultas." Es la sección "Cuándo avisar" del documento, literal. En la 20 con texto libre, como "sin apoyo" pone una frase de la documentación que la respuesta no menciona: confunde fidelidad con exhaustividad.

Así que, para lo que importa, el prompt con citas inventa claramente en 1 respuesta de 26 y el de texto libre en 4 de 25. El juez daba 10 y 11. La conclusión de fondo (las citas ayudan) se mantiene, pero los números del juez no sirven tal cual.

El juez de relevancia tiene el mismo problema. Dice que 10 de las respuestas con citas no responden a la pregunta. Entre ellas está la 22 ("Si nadie de guardia confirma una alerta crítica en 30 minutos, se avisa al responsable del equipo"), con el motivo de que "no directamente responde a la pregunta sobre qué pasa si nadie confirma la alerta". Responde exactamente a eso.

### Qué hacer con esto

- **Usa primero lo determinista.** Dato clave, abstención y citas al fragmento correcto son baratos, rápidos y no se equivocan de forma impredecible. Cubren mucho.
- **Usa el juez para priorizar, no para decidir.** Con esta calibración, sirve para ordenar qué revisar a mano, no para dar un número de fidelidad en un informe.
- **Mejora el juez con datos.** Un prompt más estricto sobre qué cuenta como apoyo, pedir que cite la frase del contexto que apoya cada afirmación, o un modelo más capaz. Y después, calibrar otra vez. Montar, calibrar y mejorar jueces es la lección 04 del módulo 4.
- **Mira el coste.** Juzgar 30 respuestas con un 7B local cuesta unos 11 segundos por llamada. Con un modelo en la nube sería más rápido y costaría dinero. En los dos casos, el juez suele ser la parte más cara de la evaluación.

## Errores frecuentes

**Fiarse del número del juez sin calibrarlo.** Es el error de esta lección. El número parece una métrica, pero mide también los sesgos del juez.

**Calibrar solo con casos que deben suspender.** Un juez que lo suspende todo los detecta todos. Incluye casos que deben aprobar.

**Pedir citas y no comprobarlas.** Una cita que nadie comprueba es decoración. Comprueba al menos que el número existe y que el fragmento citado tiene relación con la respuesta.

**Confundir fidelidad con corrección.** Una respuesta puede ser fiel al contexto y falsa, si el contexto está desactualizado (en la lección 01, la pregunta 7 tenía dos versiones del SLA en la documentación). Y puede ser verdad sin estar en el contexto: si el modelo la sabía de antes, no es fiel, y en un sistema RAG eso también es un problema.

### Anatomía de un error: la tautología en lugar de "no lo sé"

La pregunta 30 no tiene respuesta en la documentación. Con los dos prompts, el modelo contesta igualmente:

```text
[rag/con-contexto] 30. ¿Quién es el responsable del equipo Cobros?
  respuesta: El responsable del equipo Cobros es el responsable del equipo Cobros.
[rag/con-citas] 30. ¿Quién es el responsable del equipo Cobros?
  respuesta: El responsable del equipo Cobros es el equipo de Cobros.
```

**Cómo leerlo.** No hay ningún nombre inventado, que es lo que uno espera de una alucinación. Hay una frase que repite la pregunta con forma de respuesta. Las comprobaciones deterministas la cazan, porque no contiene ninguna de las frases de abstención. El juez también, por una vez con razón.

**Causa.** El contexto sí habla del responsable de Cobros. Es la sección de escalado del runbook de pagos, la que en la lección 05 el reranker puntuaba alto: "escala al responsable del equipo Cobros". El modelo encuentra la expresión exacta de la pregunta en el contexto y construye una respuesta con ella. Para un modelo de 1,5B, "la documentación menciona esto" y "la documentación responde esto" se parecen demasiado.

**Solución.** Tres capas. En el prompt: pedir que se abstenga si el contexto no da el dato concreto, no solo si no menciona el tema. En el código: detectar respuestas que repiten la pregunta (por ejemplo, con similitud muy alta entre pregunta y respuesta) y tratarlas como abstenciones. Y en la evaluación: tener preguntas sin respuesta cuyo tema sí aparezca en la documentación, como esta. Las preguntas sin respuesta sobre temas que no aparecen en ningún sitio son fáciles; estas son las que fallan.

## Bitácora

TODO(alex)

## Para profundizar

- Es et al., [Ragas: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217) (2023). Fidelidad, relevancia de la respuesta y métricas de contexto.
- Zheng et al., [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) (2023). Cuánto se parece un modelo juez a un humano, y sus sesgos.
- Gao et al., [Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627) (2023). Cómo pedir y evaluar citas.
- [Documentación de Ragas](https://docs.ragas.io/), si quieres comparar estas métricas con las de una herramienta.

---
title: "LLM-as-judge"
description: "Usar un modelo como juez: calibrarlo con etiquetas ancladas al corpus, medir su acuerdo, mejorarlo moviendo parte del juicio a código y conocer sus fallos"
---

:::note[Revisado: 2026-10]
Las salidas son reales. Los jueces son Qwen2.5 7B Instruct (rol `judge`) y Qwen2.5 1.5B Instruct, en Ollama, sobre CPU. Las respuestas evaluadas son las del RAG de las lecciones anteriores.
:::

## Objetivos

Al terminar esta lección podrás:

- Construir un conjunto de calibración para un juez, con etiquetas ancladas a segmentos del corpus.
- Medir el acuerdo de un juez con las etiquetas: sensibilidad, especificidad y kappa de Cohen.
- Mejorar un juez moviendo a código la parte del juicio que se puede comprobar.
- Reconocer los fallos y sesgos típicos de un juez, y decidir para qué usarlo y para qué no.

## Teoría

### Cuándo hace falta un juez

Las métricas deterministas de la lección 03 no pueden decidir si una respuesta parafraseada es fiel a su contexto: el modelo reescribe, resume y combina. Para eso se usa otro modelo como evaluador: el patrón **LLM-as-judge**. Lo viste en la lección 06 del módulo 3, y también viste su problema: aquel juez rechazaba respuestas fieles que copiaban el contexto palabra por palabra.

Un juez es un modelo, así que tiene sus fallos y sus sesgos. Los más documentados:

- **Severidad descompensada.** Un juez que suspende de más o que aprueba de más. Los dos dan números que parecen métricas.
- **Posición.** Cuando compara dos respuestas, tiende a preferir la primera (o la segunda) independientemente del contenido.
- **Longitud.** Tiende a puntuar mejor las respuestas largas.
- **Autopreferencia.** Tiende a preferir textos de su misma familia de modelos.
- **Forma frente a fondo.** Un tono seguro, una cita a una fuente o un formato cuidado pueden pesar más que el contenido.

Por eso un juez no se usa sin **calibrarlo**: medir cuánto coincide con un criterio humano en casos cuya respuesta se conoce.

### Etiquetas de calibración ancladas al corpus

Calibrar exige etiquetas: casos en los que alguien ha decidido, con criterio, si la respuesta es fiel o no. Y aquí vale el mismo principio que en la lección 02: las etiquetas tienen que estar **ancladas al corpus**. En [`juez_etiquetas.jsonl`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/datos/juez_etiquetas.jsonl), cada respuesta fiel lleva los segmentos literales del contexto que la apoyan, y cada respuesta no fiel lleva la afirmación concreta que no tiene apoyo:

```json
{"id": "real-m3-19", "respuesta": "Si perdemos el índice de búsqueda, se tarda en reconstruirlo alrededor de 4 horas, …",
 "fiel": false, "sin_apoyo": ["se tarda en reconstruirlo alrededor de 4 horas"],
 "nota": "Las 4 horas son de la restauración de usuarios, no del índice de búsqueda."}
```

Un test comprueba que cada apoyo está literalmente en el contexto y cada afirmación, en la respuesta. Así, una etiqueta no puede decir "lo apoya el contexto" sin decir dónde.

Hay 64 etiquetas. 46 son respuestas reales del sistema de la lección 02: 35 fieles y 11 no fieles. Las otras 18 son respuestas fieles alteradas a propósito, con la etiqueta conocida por construcción: 8 con un dato cambiado, 6 con una afirmación inventada añadida y 4 con una invención presentada con autoridad ("Según el runbook…"). Las alteraciones equilibran las clases y permiten ver qué tipo de fallo detecta cada juez.

Etiquetar exige decidir criterios, y algunos casos no son obvios. Por ejemplo, la respuesta n-06 dice "99,9 %", que es lo que pone el contexto que recibió el modelo: es **fiel**, aunque sea incorrecta, porque el SLA vigente no llegó al contexto. Fidelidad y corrección son cosas distintas. Si no estás de acuerdo con alguna etiqueta, cámbiala y vuelve a medir: el criterio es tuyo.

### Medir el acuerdo

"El juez acierta el 83 %" no basta, porque depende de cuántos casos de cada clase haya. Se mira la **matriz de confusión**, con "positivo" = el problema que busca el juez (una respuesta no fiel):

- **Sensibilidad**: de las respuestas no fieles, cuántas detecta.
- **Especificidad**: de las fieles, cuántas deja pasar sin dar la alarma.
- **Kappa de Cohen**: el acuerdo descontando el que se daría por azar. 0 es azar; 1, acuerdo perfecto. Un juez que siempre da la misma respuesta tiene kappa 0, aunque acierte mucho si una clase domina.

`curso_core.evals.acuerdo` calcula las cuatro cifras.

### Mover el juicio a código

El juez de la lección 06 del módulo 3 (aquí, **v1**) decide él solo si la respuesta es fiel. El **v2** ([`rag/juez-fidelidad-citas`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/rag/juez-fidelidad-citas.md)) cambia el reparto de trabajo. El modelo divide la respuesta en afirmaciones y copia, para cada una, la frase literal del contexto que la apoya. El veredicto lo da el código: la respuesta es fiel si todas las afirmaciones tienen una cita **y esa cita existe en el contexto**.

Es aplicar al juez la misma idea que al dataset: lo que se puede anclar a un segmento literal se comprueba con código, y el modelo solo hace lo que el código no puede (entender qué afirma una frase y dónde se apoya).

## Práctica

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/calibrar_juez.py
```

[`calibrar_juez.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/calibrar_juez.py) pasa los tres jueces por las 64 etiquetas y guarda sus veredictos. Son unas 190 llamadas a modelos y, en la máquina del curso, unos 40 minutos; con `--grabadas` usa los veredictos guardados y tarda un segundo. La salida:

```text
1. 64 etiquetas (29 no fieles). Positivo = no fiel
   juez            VP  FP  FN  VN  acuerdo  detecta  no alarma  kappa  mediana s
   juez-v1-7b      29  11   0  24     83%     100%        69%   0.66       11.2
   juez-v2-7b      24   3   5  32     88%      83%        91%   0.75       16.7
   juez-v2-1.5b    13   7  16  28     64%      45%        80%   0.26        4.3

2. Aciertos de cada juez por origen de la etiqueta
                               juez-v1-7b    juez-v2-7b  juez-v2-1.5b
   real, fiel                    24 de 35      32 de 35      28 de 35
   real, no fiel                 11 de 11       7 de 11       6 de 11
   dato_cambiado, no fiel         8 de  8       8 de  8       3 de  8
   afirmacion_añadida, no fiel     6 de  6       6 de  6       3 de  6
   autoridad, no fiel             4 de  4       3 de  4       1 de  4

3. Desacuerdos de juez-v2-7b con las etiquetas
   real-m3-19 (etiqueta: no fiel, juez: fiel)
     respuesta: 'Si perdemos el índice de búsqueda, se tarda en reconstruirlo alrededor de 4 horas, según el postmortem de la p'
   real-m3-21 (etiqueta: no fiel, juez: fiel)
     respuesta: 'La alerta PagosLatenciaP95Alta saltó a los 3 minutos.'
   real-m3-26 (etiqueta: no fiel, juez: fiel)
     respuesta: 'No, no es necesario avisar a la atención al cliente de una incidencia de severidad media.'
   real-m3-30 (etiqueta: no fiel, juez: fiel)
     respuesta: 'El responsable del equipo Cobros es el responsable del escalado.'
   real-n-02 (etiqueta: fiel, juez: no fiel)
     respuesta: 'El perfil_edicion es un interruptor de funcionalidad que permite desactivar temporalmente la edición de perfil'
     sin cita según el juez: ['para evitar deadlocks en la base de datos de usuarios']
   real-n-05 (etiqueta: fiel, juez: no fiel)
     respuesta: '99,5 %'
     citas que no están en el contexto: ['pagos | 99,95 % | usuarios | 99,9 % | catalogo | 99,9 % | notificaciones | 99,5 % | busqueda | 99,5 % |']
   real-s-06 (etiqueta: fiel, juez: no fiel)
     respuesta: 'La persona de guardia en catálogo esta semana es la que atiende las alertas de producción de su equipo y tiene'
     sin cita según el juez: ['La persona de guardia en catálogo esta semana es la que atiende las alertas de producción de su equipo']
   autoridad-n-11 (etiqueta: no fiel, juez: fiel)
     respuesta: 'La persona de guardia puede cambiar la severidad que se ha propuesto para una incidencia. Así lo indica la pol'

4. El juez v2 comparando las citas sin el formato de las tablas (sin modelo)
   juez            VP  FP  FN  VN  acuerdo  detecta  no alarma  kappa  mediana s
   juez-v2-7b      24   2   5  33     89%      83%        94%   0.78       16.7
   juez-v2-1.5b    13   7  16  28     64%      45%        80%   0.26        4.3
```

## Mide y depura

### El v1 detecta todo porque sospecha de todo

El juez v1 no deja pasar ninguna respuesta no fiel: 29 de 29. Visto solo así, parece perfecto. Pero rechaza 11 de las 35 respuestas reales fieles. Es lo mismo que viste en el módulo 3: un juez que suspende de más detecta todas las trampas. La especificidad (69 %) y la kappa (0,66) lo delatan; la sensibilidad sola, no.

### El v2: menos falsas alarmas, algunos fallos que se le escapan

Haciendo que el juez cite y que el código compruebe, las falsas alarmas bajan de 11 a 3, y el acuerdo sube del 83 % al 88 % (kappa 0,75). A cambio, deja pasar 5 de las 29 respuestas no fieles. Y tarda más (16,7 s de mediana frente a 11,2 s), porque escribe una cita por afirmación.

Una de las 3 falsas alarmas tenía arreglo en el propio código. En la n-05, el juez copió la fila de la tabla del SLA sin sus barras ni sus saltos de línea, y la comparación literal no la encontró. Si la comparación ignora el formato de las tablas (`cita_valida`), las falsas alarmas bajan a 2 y la kappa sube a 0,78. Como las citas no encontradas estaban guardadas, el nuevo veredicto se recalcula sin volver a llamar al modelo: es la parte 4.

### Dos maneras de engañar al v2

Mirando qué citó el juez en las 5 respuestas no fieles que dio por buenas, aparecen dos fallos distintos. (La primera versión de `juez_v2` solo guardaba las citas que no encontraba, así que estas se obtuvieron repitiendo esas llamadas, con temperatura 0. La versión actual guarda todas.)

1. **La cita existe, pero no dice eso.** En la m3-26, la respuesta afirma "No, no es necesario avisar a la atención al cliente de una incidencia de severidad media", y el juez la apoya con "Avisa siempre en las incidencias críticas y altas que afecten a clientes. En las medias, solo si generan consultas". La cita existe, así que el código la acepta, pero dice otra cosa. Lo mismo en la m3-19 (cita las 4 horas de la restauración de usuarios) y en la m3-21 (cita "La alerta saltó a los 3 minutos", de otra alerta). Es el mismo problema que el reranker de la lección 05 del módulo 3: una frase relacionada no es una frase que lo apoye.
2. **Se salta una afirmación.** En la autoridad-n-11, el juez solo lista la primera frase de la respuesta. La invención añadida ("Así lo indica la política de severidades, que también permite cambiarla al responsable del equipo") ni siquiera aparece entre las afirmaciones, así que nunca se comprueba.

El código cubre lo que se puede comprobar de forma literal (que la cita exista). Lo que no cubre (que la cita implique la afirmación, que no falte ninguna afirmación) sigue dependiendo del modelo. El segundo fallo sí admite más código: comprobar que las afirmaciones del juez cubren todas las frases de la respuesta.

### El modelo pequeño no sirve de juez

Con el modelo de 1,5B, el mismo juez v2 detecta el 45 % de las respuestas no fieles y su kappa es 0,26. Es cuatro veces más rápido, pero la comprobación con código no compensa que el modelo no sepa dividir la respuesta en afirmaciones ni encontrar la frase que las apoya. Para juzgar, usa un modelo más capaz que el que genera.

### Para qué sirve, entonces

Con kappa 0,78, el juez v2 es útil para **priorizar**. Cuando da la alarma, acierta en 24 de 26 casos: si revisas a mano las respuestas que marca, casi todas son problemas reales. No sirve como cifra absoluta de fidelidad, porque deja pasar el 17 % de las invenciones. Y cualquier cambio en el juez (prompt, modelo, comprobación) se valida igual que se ha hecho aquí: contra las mismas etiquetas, mirando sensibilidad, especificidad y kappa, no solo el acuerdo.

Con 64 etiquetas, estas cifras también tienen margen de error (lección 03). Sirven para comparar jueces sobre los mismos casos y para ver tendencias, no para afirmar que la kappa es exactamente 0,78.

## Errores frecuentes

**Usar un juez sin calibrar.** Su número parece una métrica y mide también sus sesgos. Calibra con etiquetas de las dos clases.

**Mirar solo la sensibilidad.** Un juez que lo rechaza todo la tiene perfecta. Mira también la especificidad y la kappa.

**Etiquetar sin anclar.** "Esta respuesta es fiel" sin decir qué frase la apoya es una opinión. Con el segmento al lado, la etiqueta se puede revisar.

**Dejar al juez lo que puede hacer el código.** Que una cita exista se comprueba con código, siempre y sin errores. Pide al juez lo que el código no puede hacer y comprueba el resto.

**Usar como juez el mismo modelo pequeño que genera.** Si el generador comete un error, es probable que el juez no lo vea.

### Anatomía de un error: la cita que existe pero dice lo contrario

```text
real-m3-26 (etiqueta: no fiel, juez: fiel)
  respuesta: 'No, no es necesario avisar a la atención al cliente de una incidencia de severidad media.'
  cita del juez: 'Avisa siempre en las incidencias críticas y altas que afecten a clientes. En las medias, solo si generan consultas.'
```

**Cómo leerlo.** El juez v2 dio la respuesta por fiel: encontró una afirmación, la apoyó con una cita y el código comprobó que la cita está en el contexto. Todo el procedimiento se cumplió. Pero la cita dice que en las incidencias medias se avisa si generan consultas, y la respuesta dice que no hay que avisar.

**Causa.** El código comprueba que la cita existe, no que apoye la afirmación. Esa segunda parte la hace el modelo, y el modelo eligió la frase que habla del tema (avisar a atención al cliente según la severidad) sin comprobar que dijera lo mismo. Una frase relacionada pasa por una frase de apoyo.

**Solución.** Hay varias, y todas se validan contra las etiquetas: pedir al juez que, además de citar, diga si la cita implica la afirmación (una segunda pregunta, más concreta); usar un modelo de inferencia textual entrenado para eso (NLI, *natural language inference*); o, como mínimo, conocer este fallo y no usar el veredicto "fiel" del juez como garantía. Cuando el juez marca una respuesta como no fiel, acierta casi siempre; cuando la marca como fiel, se le pueden colar respuestas así.

## Para profundizar

- Zheng et al., [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) (2023). Los sesgos de posición, longitud y autopreferencia, medidos.
- Thakur et al., [Judging the Judges: Evaluating Alignment and Vulnerabilities in LLMs-as-Judges](https://arxiv.org/abs/2406.12624) (2024). Por qué el porcentaje de acuerdo no basta y conviene usar kappa.
- Shankar et al., [Who Validates the Validators?](https://arxiv.org/abs/2404.12272) (2024). Alinear los criterios de un juez con los de las personas que lo usan.
- [Cohen's kappa](https://en.wikipedia.org/wiki/Cohen%27s_kappa) en Wikipedia.

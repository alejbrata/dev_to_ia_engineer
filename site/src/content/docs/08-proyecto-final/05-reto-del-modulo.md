---
title: "Reto del módulo: un problema que no conoces"
description: "Reto final del curso, sin solución guiada: construir desde cero un asistente sobre documentos que no has visto, medirlo con 20 preguntas de desarrollo y validarlo una sola vez con otras 20 de prueba"
---

:::note[Revisado: 2026-11]
Las salidas son reales, con los modelos de los roles `chat` (Qwen2.5 1,5B), `chat_grande` (Qwen2.5 7B) y `embeddings` (bge-m3) en Ollama sobre CPU. Puedes usar los que quieras o puedas: los nombres están en `config/models.toml`.
:::

Los retos de los módulos anteriores te daban un código con fallos. Este no: te da un problema, los datos y una forma de medir. El sistema lo construyes tú, con lo que has aprendido. La solución de referencia está en el repositorio, pero no es la respuesta: es una forma de llegar, con la que comparar la tuya.

## Objetivos

- Construir un asistente sobre documentos que no has visto, eligiendo las piezas y justificando cada una con una medida.
- Separar el trabajo con desarrollo de la validación con prueba, y mirar la prueba una sola vez.
- Leer los fallos de tu sistema y decir si son del sistema o de la eval.

## El reto

Arce Distribución, una empresa inventada, quiere un asistente que responda a su plantilla sobre las políticas internas. Las políticas están en [`reto/docs/`](https://github.com/alejbrata/dev_to_ia_engineer/tree/main/modulos/08-proyecto-final/reto/docs): ocho documentos en Markdown sobre vacaciones, teletrabajo, viajes y gastos, equipos, formación, horario, permisos y seguridad de la información. No salen en ninguna lección.

Si algo no está en las políticas, el asistente tiene que decir "No aparece en la documentación". Es una empresa con datos de personas: inventar una cifra de una nómina o de un permiso es peor que no responder.

Hay dos juegos de preguntas, cada una con los datos clave que tiene que llevar la respuesta:

- **Desarrollo** (`preguntas-desarrollo.jsonl`): 20 preguntas, 4 sin respuesta en las políticas. Son para trabajar: míralas, mide, cambia y vuelve a medir.
- **Prueba** (`preguntas-prueba.jsonl`): otras 20, también con 4 sin respuesta. Son para el final. Están en el repositorio porque el curso es abierto, pero si las lees antes de terminar, la cifra de prueba deja de decir lo que el sistema hará con preguntas que no conoce (lección 4.06).

Algunas preguntas piden varios pasos, y la respuesta tiene que darlos todos. Si te roban el portátil, hay que avisar a Soporte y poner la denuncia: con una sola de las dos, la respuesta está incompleta.

[`reto/asistente.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/08-proyecto-final/reto/asistente.py) es la línea base: el modelo responde sin los documentos. La única regla es la firma: `responder(cliente, pregunta)` devuelve el texto de la respuesta. Lo demás (troceado, búsqueda, reranker, prompt, modelo, guardrails) lo eliges tú.

## Criterios de aceptación

En desarrollo:

1. Al menos 16 de las 20 preguntas, bien.
2. Se abstiene en al menos 3 de las 4 que no tienen respuesta.

En prueba, una sola vez, al final:

3. Al menos 15 de las 20, bien.
4. Se abstiene en al menos 3 de las 4 que no tienen respuesta.

Una respuesta está bien si contiene todos sus datos clave y no se abstiene. En una pregunta sin respuesta, está bien si se abstiene. Prueba pide algo menos que desarrollo a propósito: un sistema afinado con unas preguntas suele bajar con otras, y lo honesto es esperarlo.

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/08-proyecto-final/reto/comprobar.py) llama a tu `responder` con cada pregunta y puntúa. Usa tus modelos: con la línea base, unos 20 segundos. Con la línea base, en desarrollo:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/08-proyecto-final/reto/comprobar.py
```

```text
Reto del módulo 8 · reto/asistente.py · desarrollo · rol chat · 19 s
   FALLA desarrollo: al menos 16 de 20 bien: 3 de 20, IC 95 % 5%-36% (mal: d01, d02, d03, d04, d05, d06, d07, d08, d09, d11, d12, d13, d14, d15, d16, d19, d20)
   FALLA desarrollo: se abstiene en al menos 3 de las 4 que no tienen respuesta: 2 de 4
0 de 2 criterios. Sigue: lee el primero que falla.
```

Sin documentos, el modelo acierta 3 de 20 e inventa en 2 de las 4 que no tienen respuesta. Esa es tu línea base: cualquier pieza que añadas tiene que mejorarla, y la mejora se mide (lección 7.01).

Cuando estés conforme con desarrollo:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/08-proyecto-final/reto/comprobar.py --prueba
```

Cada ejecución con `--prueba` se anota en `reto/resultados/prueba.log`, que no se versiona. A partir de la segunda, el comprobador avisa. No te lo impide: decide tú si una segunda mirada sigue siendo una prueba.

## Pistas

No hay pistas sobre qué construir: es el reto. Solo dos sobre cómo trabajar.

<details>
<summary>Pista 1: por dónde empezar</summary>

Por lo más simple que pueda funcionar, medido: los documentos troceados, una búsqueda y un prompt. Después, una pieza cada vez, y cada una con su medida en desarrollo. Si una pieza no mejora la cifra, no la dejes "por si acaso" (lección 4.05).

</details>

<details>
<summary>Pista 2: cuando falla una pregunta</summary>

Antes de cambiar nada, mira en qué etapa se pierde (lección 4.05): ¿llega al contexto el fragmento con el dato? Si llega, el fallo es de la generación. Si no llega, es de la recuperación. Y lee la respuesta: puede que esté bien y que el fallo sea de la eval.

</details>

## La solución de referencia

Está en [`reto/solucion/asistente.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/08-proyecto-final/reto/solucion/asistente.py). Es el RAG del curso sin piezas nuevas:

- troceado por secciones con su título (lección 3.02);
- búsqueda densa con 3 fragmentos (lección 3.03);
- un prompt que responde solo con los fragmentos, da todos los pasos y se abstiene si el dato no está (lecciones 3.06 y 4.06);
- el modelo de 7B.

Se comprueba con `comprobar.py --solucion`. En desarrollo, con los dos modelos:

```text
Reto del módulo 8 · reto/solucion/asistente.py · desarrollo · rol chat · 49 s
   OK    desarrollo: al menos 16 de 20 bien: 17 de 20, IC 95 % 64%-95% (mal: d07, d16, d17)
   OK    desarrollo: se abstiene en al menos 3 de las 4 que no tienen respuesta: 3 de 4
Reto superado: 2 de 2 criterios.
Reto del módulo 8 · reto/solucion/asistente.py · desarrollo · rol chat_grande · 186 s
   OK    desarrollo: al menos 16 de 20 bien: 19 de 20, IC 95 % 76%-99% (mal: d07)
   OK    desarrollo: se abstiene en al menos 3 de las 4 que no tienen respuesta: 4 de 4
Reto superado: 2 de 2 criterios.
```

Con el 1,5B ya se cumplen los criterios, y es casi cuatro veces más rápido. Pero en una de las cuatro preguntas sin respuesta, la d17 ("¿Cuántos días de vacaciones extra tengo por antigüedad?"), responde con los 23 días de vacaciones generales. Es un dato real, pero no el que se pregunta: las políticas no dicen nada de la antigüedad, y quien lea la respuesta entenderá que no hay días extra. En un asistente de Personas, eso pesa más que la velocidad, y por eso la referencia usa el 7B. Es una decisión, no un resultado: la tuya puede ser otra, si la justificas con tus medidas.

Y en prueba, una vez:

```text
Reto del módulo 8 · reto/solucion/asistente.py · prueba · rol chat_grande · 164 s
   OK    prueba: al menos 15 de 20 bien: 17 de 20, IC 95 % 64%-95% (mal: p03, p07, p08)
   OK    prueba: se abstiene en al menos 3 de las 4 que no tienen respuesta: 4 de 4
Reto superado: 2 de 2 criterios.
```

De 19 en desarrollo a 17 en prueba. Los cuatro fallos, entre las dos particiones, son el mismo: el sistema se abstiene cuando sí tenía el dato.

- **d07**, "¿Puedo ir en avión a un viaje de 3 horas?": la política dice que en viajes de menos de 4 horas se va en tren.
- **p03**, "¿Me pagan las vacaciones que no disfruto?": no, salvo al terminar la relación laboral.
- **p07**, "¿Cuánto puede costar como máximo el hotel en Sevilla?": 120 euros, porque los 180 son solo para Madrid y Barcelona.
- **p08**, "¿La dieta cubre el vino de la cena?": el alcohol no se paga.

En los cuatro, la respuesta no está escrita con las palabras de la pregunta, y hay que deducirla. La regla del prompt ("no respondas con un dato parecido de otra política") evita inventar y, de paso, frena estas deducciones. Es el equilibrio de la lección 3.06 entre abstenerse de más y de menos. Aquí la referencia se queda del lado prudente: no inventa en ninguna de las 8 preguntas sin respuesta y falla 4 de las 32 que sí la tienen. Mover esa línea es la siguiente iteración, y se mide igual.

Si tu sistema supera los criterios, ya tienes un proyecto que contar en una entrevista: la línea base, cada decisión con su medida, la cifra de prueba con su intervalo y los fallos que quedan, explicados. Es lo que pide el proyecto final (lecciones 01 a 04), en pequeño.

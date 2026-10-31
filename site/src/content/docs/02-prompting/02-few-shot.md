---
title: "Few-shot, técnicas y mitos"
description: "Few-shot y técnicas que sí funcionan (y mitos que no)"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el modelo con el que se construyó el curso (Qwen2.5 1.5B Instruct en Ollama), temperatura 0. Las técnicas que funcionan con un modelo pueden no funcionar con otro: lo que se aprende aquí es a comprobarlo.
:::

## Objetivos

Al terminar esta lección podrás:

- Añadir ejemplos resueltos (few-shot) a un prompt y elegirlos sin contaminar la evaluación.
- Medir el efecto de una técnica de prompting en lugar de darlo por hecho.
- Distinguir una mejora real del ruido cuando solo tienes diez casos.
- Comparar variantes de un prompt en las mismas condiciones.

## Teoría

### Enseñar con ejemplos

En la lección anterior, el modelo leía criterios ("critica: el servicio está caído para todos...") y aun así se equivocaba con la severidad. Hay otra forma de explicarle lo que quieres: **mostrárselo**. Un prompt few-shot incluye unos cuantos casos resueltos antes del caso real. Se mandan como pares de mensajes: un mensaje de usuario con un ticket y uno de asistente con su clasificación.

```markdown
## Ejemplos

### Usuario
Ticket:
El despliegue de usuarios ha ejecutado una migración que ha borrado la columna 'telefono'...

### Asistente
categoria: despliegue
severidad: critica
servicio: usuarios
```

Los ejemplos hacen dos cosas a la vez: enseñan el **formato** exacto (el modelo imita lo que ve) y enseñan **criterio** (cómo se resuelven casos parecidos). Cuestan tokens en cada llamada: cinco ejemplos casi duplican la entrada del prompt.

### Ejemplos y evaluación, por separado

Los ejemplos salen del grupo `ejemplos` de los tickets, nunca del grupo `eval`. Si usaras un caso de evaluación como ejemplo, el modelo vería la respuesta antes de que le preguntes y la medición dejaría de valer. Es el mismo principio que no entrenar con los datos de test. En este curso, la separación está en los propios datos: cada ticket lleva su grupo.

### Técnicas populares

Circulan muchas recetas para "mejorar" prompts. Algunas funcionan con algunos modelos, otras son folclore. Dos de las más repetidas:

- **"Eres el mejor experto del mundo".** Exagerar el rol del modelo para que responda "mejor".
- **"Razona paso a paso".** Pedir al modelo que explique su razonamiento antes de responder. Con modelos grandes y tareas de razonamiento puede ayudar; tiene un coste en tokens de salida.

Aquí no se dan por buenas ni por malas: se miden con los mismos diez tickets.

## Práctica

[`few_shot.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/few_shot.py) mide seis variantes del prompt, todas derivadas de `tickets/completo` (lección 01):

| Variante | Qué cambia |
| --- | --- |
| [`completo`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/completo.md) | Nada: la referencia |
| [`few-shot-2`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/few-shot-2.md) | 2 ejemplos resueltos |
| [`few-shot-5`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/few-shot-5.md) | 5 ejemplos, uno o más de cada severidad |
| [`experto`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/experto.md) | "Eres el mejor experto del mundo... Nunca te equivocas." |
| [`paso-a-paso`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/paso-a-paso.md) | "Antes de responder, razona paso a paso" |
| [`sesgado`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/prompts/tickets/sesgado.md) | 3 ejemplos, todos de la categoría rendimiento (mal elegidos a propósito) |

Tarda unos dos minutos: antes de cada variante descarga el modelo para que todas empiecen igual.

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/02-prompting/few_shot.py
```

```text
variante                   utilizables categoría severidad servicio las 3 tokens latencia
tickets/completo@v1               8/10       6/10       4/10      7/10   3/10    345    1.12s
tickets/few-shot-2@v1            10/10       8/10       8/10      7/10   3/10    465    1.18s
tickets/few-shot-5@v1            10/10       9/10       5/10      9/10   4/10    645    1.28s
tickets/experto@v1               10/10       5/10       6/10      9/10   3/10    368    1.07s
tickets/paso-a-paso@v1           10/10       8/10       6/10      8/10   4/10    373    1.10s
tickets/sesgado@v1                9/10       9/10       6/10      8/10   5/10    515    1.24s

(tokens: entrada media por ticket · latencia: media por ticket)

Tickets que son de rendimiento: 2 de 10
  tickets/completo@v1        los clasifica como rendimiento:  2 · tokens de salida medios: 17
  tickets/few-shot-2@v1      los clasifica como rendimiento:  1 · tokens de salida medios: 17
  tickets/few-shot-5@v1      los clasifica como rendimiento:  2 · tokens de salida medios: 17
  tickets/experto@v1         los clasifica como rendimiento:  0 · tokens de salida medios: 16
  tickets/paso-a-paso@v1     los clasifica como rendimiento:  2 · tokens de salida medios: 17
  tickets/sesgado@v1         los clasifica como rendimiento:  2 · tokens de salida medios: 17
```

Con `--detalle`, el script muestra ticket a ticket qué respondió cada variante.

## Mide y depura

### Qué dicen los datos

Lee la tabla columna a columna, no solo la última:

- **El formato mejora con cualquier cambio.** Todas las variantes dan 9 o 10 respuestas utilizables, frente a las 8 de la referencia. Los dos fallos de formato de la referencia (los tickets 2 y 6, donde mezclaba campos) desaparecen al tocar el prompt, con ejemplos o sin ellos. No es un mérito exclusivo de los ejemplos.
- **Los ejemplos mejoran la categoría.** Las tres variantes con ejemplos aciertan 8 o 9 categorías; las tres sin ejemplos, 5, 6 y 8. Es el efecto más consistente de la tabla.
- **"Experto" no ayuda.** Peor categoría que la referencia (5 frente a 6) y los mismos aciertos completos.
- **"Paso a paso" ni siquiera se cumple.** Mira los tokens de salida: 17 de media, los mismos que las demás variantes. El modelo no razona: contesta directamente las tres líneas. Lo que cambie en sus resultados no viene del razonamiento.
- **Los ejemplos sesgados no sesgan.** Con tres ejemplos de rendimiento, el modelo sigue clasificando como rendimiento solo los 2 tickets que lo son. Era una hipótesis razonable (el modelo copia lo que ve) y con este modelo y estos casos no se cumple. Cualquier ejemplo, incluso mal elegido, le enseñó el formato.

### Lo que los datos no dicen

En la columna de las tres respuestas correctas, todas las variantes están entre 3 y 5 de 10. Con diez casos, un ticket más o menos es un 10 %, y la diferencia entre 3 y 5 puede deberse a dos tickets que caen de un lado o del otro. **Con estos datos no puedes decir que una variante sea mejor que otra en el resultado completo.** Puedes decir que los ejemplos mejoran el formato y la categoría, porque esa diferencia es grande y se repite.

Para decidir con más seguridad necesitas más casos y medir varias veces. Es exactamente lo que harás en la lección 06 y en el módulo de evals.

### Medir en las mismas condiciones

El script descarga el modelo antes de cada variante. No es un capricho: sin eso, las cifras cambian según qué variante se ejecutó antes. Lo verás en la anatomía del error.

## Errores frecuentes

**Creer una técnica porque la has leído.** "Experto" y "paso a paso" se repiten como recetas universales. Con este modelo, una empeora la categoría y la otra ni se aplica. Mide con tu modelo y tus datos.

**Sacar los ejemplos de los casos de evaluación.** La nota sube por haber visto las respuestas, no por haber aprendido. Separa siempre los dos grupos.

**Mirar solo el número final.** "Las 3" casi no se mueve, pero debajo hay mejoras claras (formato, categoría) y retrocesos (severidad con 5 ejemplos). Una sola cifra esconde lo que necesitas saber para la siguiente iteración.

**Olvidar el coste de los ejemplos.** Cinco ejemplos casi duplican los tokens de entrada (645 frente a 345). En un modelo de pago, eso es casi el doble en la parte de entrada del coste.

### Anatomía de un error: la mejora que dependía del orden

La primera versión de este script medía las seis variantes una detrás de otra, sin descargar el modelo entre ellas. El resultado de `few-shot-5` fue:

```text
tickets/few-shot-5@v1            10/10       9/10       7/10      9/10   6/10    645    1.07s
```

Seis de diez, el doble que la referencia. Parecía la mejora clara que buscabas. Repetido con el mismo orden, salía exactamente igual. Pero midiéndola sola, con el modelo recién cargado:

```text
tickets/few-shot-5@v1            10/10       9/10       5/10      9/10   4/10    645    1.28s
```

Cuatro de diez. Mismo prompt, mismos tickets, temperatura 0.

**Cómo leerlo.** El cambio está en la severidad (de 7 a 5) y, con ella, en el resultado completo. La categoría y el servicio no se mueven. Si el resultado depende de lo que se ejecutó antes, el número no mide solo el prompt: mide también el estado del servidor.

**Causa.** Todas las variantes comparten el mismo mensaje de sistema. Ollama reutiliza el cálculo de los tokens que ya ha visto (la caché del prompt de la lección 06 del módulo 1). Las cuentas con y sin caché dan probabilidades casi iguales, pero no idénticas bit a bit, y en las decisiones reñidas (la severidad lo es) eso basta para cambiar la respuesta. Es el mismo efecto que viste en la lección de sampling con la semilla.

**Solución.** Compara variantes **en las mismas condiciones**: este script descarga el modelo antes de cada una. Y desconfía de cualquier mejora de uno o dos casos: repite la medición, cambia el orden, añade casos. Si la mejora no sobrevive a eso, no era una mejora.

## Bitácora

TODO(alex)

## Para profundizar

- Brown et al., [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) (2020). El artículo de GPT-3 que popularizó el aprendizaje con ejemplos en el prompt.
- Wei et al., [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) (2022). El origen de "razona paso a paso", con sus resultados en modelos grandes.
- [Ingeniería de prompts](https://huggingface.co/docs/transformers/tasks/prompting) en la documentación de Hugging Face, con su sección sobre few-shot.

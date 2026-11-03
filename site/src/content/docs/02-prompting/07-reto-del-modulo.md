---
title: "Reto del módulo: el extractor que valida pero miente"
description: "Reto del módulo 2, sin solución guiada: un extractor de avisos de incidencias cuyo JSON siempre cumple el esquema y aun así dice cosas falsas; arreglar el prompt, el esquema y el modelo hasta pasar una eval por campos"
---

:::note[Revisado: 2026-11]
Las salidas son reales, con los modelos de los roles `chat` (Qwen2.5 1,5B) y `chat_grande` (Qwen2.5 7B) en Ollama sobre CPU. Puedes usar los que quieras o puedas: los nombres están en `config/models.toml`.
:::

Tienes un extractor con fallos, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio: ábrela al final, para comparar.

## Objetivos

- Distinguir una salida estructuralmente válida de una correcta, y medir la segunda campo a campo.
- Encontrar en un prompt lo que el modelo copia (un ejemplo mal etiquetado) y lo que le falta (los criterios).
- Hacer que el esquema exija lo que hoy solo pide el prompt.
- Decidir con datos si el problema se arregla con el prompt o hace falta otro modelo.

## El reto

El equipo de guardia recibe correos que avisan de incidencias. [`reto/extractor.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/reto/extractor.py) convierte cada uno en un aviso estructurado: el servicio, la severidad, si afecta a clientes y la hora de inicio. Usa salida estructurada con Pydantic (lección 03) y un prompt versionado en un fichero aparte, [`reto/extraer-aviso.md`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/reto/extraer-aviso.md) (lección 05).

El JSON siempre cumple el esquema: Pydantic no se queja nunca. Estos son tres avisos reales del extractor:

```text
Desde las 16:30 se cobran dos veces algunos pedidos. Ya hay clientes reclamando el cargo duplicado.
{"servicio":"pagos","severidad":"alta","afecta_clientes":true,"hora_inicio":"16:30"}

Desde las 6:00 los productos nuevos tardan horas en aparecer en la búsqueda; los que ya estaban se encuentran bien.
{"servicio":"busqueda","severidad":"media","afecta_clientes":true,"hora_inicio":"6:00"}

El proceso interno que genera el informe semanal del catálogo para el equipo de producto falla desde el lunes.
{"servicio":"catalogo","severidad":"alta","afecta_clientes":false,"hora_inicio":"lunes"}
```

Los tres son válidos y los tres dicen algo falso o inservible. Un cobro duplicado es pérdida de dinero, y según los criterios del equipo eso es crítica. "6:00" no tiene el formato que espera quien lo lee. Y "lunes" no es una hora.

Los 15 correos y lo que debería salir de cada uno están en `reto/correos.jsonl`. Puedes cambiar el prompt, el esquema y el rol del modelo (`ROL`), pero no los correos ni las respuestas esperadas.

## Criterios de aceptación

De los 15 correos:

1. El servicio está bien en al menos 14.
2. La hora de inicio está bien en al menos 14: en formato `HH:MM` de 24 horas, o `null` si el correo no la dice.
3. Si afecta a clientes está bien en al menos 14.
4. La severidad está bien en al menos 10.
5. Al menos 10 avisos están bien enteros.

La severidad pide menos que los demás campos a propósito. Es la decisión difícil, y con 15 correos, perseguir el 15 de 15 retocando el prompt es ajustarlo a estos correos, no mejorarlo (módulo 4).

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/02-prompting/reto/comprobar.py) extrae los 15 avisos con tu prompt, tu esquema y tu rol, y mide cada campo, como la eval de la lección 06. Llama al modelo: unos 30 segundos con el de 1,5B y unos 3 minutos con el de 7B. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/02-prompting/reto/comprobar.py
```

```text
Reto del módulo 2 · reto/extractor.py · rol chat · 31 s
   FALLA servicio: al menos 14 de 15: 11 de 15 (mal: 4, 10, 11, 12)
   FALLA hora_inicio: al menos 14 de 15: 10 de 15 (mal: 5, 8, 11, 12, 14)
   OK    afecta_clientes: al menos 14 de 15: 14 de 15 (mal: 8)
   FALLA severidad: al menos 10 de 15: 6 de 15 (mal: 1, 5, 6, 7, 8, 9, 11, 13, 14)
   FALLA avisos enteros correctos: al menos 10 de 15: 3 de 15
1 de 5 criterios. Sigue: lee el primero que falla.
```

Aunque la temperatura sea 0, Ollama no siempre da exactamente lo mismo de una ejecución a otra: un caso puede cambiar. Los mínimos dejan margen para eso. El reto está superado cuando dice `Reto superado: 5 de 5 criterios.`.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: la severidad</summary>

Lee los dos ejemplos del prompt como si fueras el modelo. ¿Qué severidad le pone uno de ellos a unos clientes que no pueden pagar? ¿Y dónde dice el prompt qué significa cada severidad? Los criterios del equipo están en la documentación del módulo 3 (`severidades.md`).

</details>

<details>
<summary>Pista 2: la hora</summary>

El esquema dice `hora_inicio: str | None`. Cualquier texto lo cumple. Pydantic puede exigir un formato a un campo de texto, y con salida estructurada el servidor impone el esquema al generar (lección 03).

</details>

<details>
<summary>Pista 3: si la severidad no sube</summary>

El modelo escribe el JSON de izquierda a derecha, y la severidad va casi al principio. ¿Ha "pensado" algo antes de decidirla? Y si con un buen prompt sigue sin llegar, mide el mismo prompt con otro rol.

</details>

## La solución

Está en [`reto/solucion/`](https://github.com/alejbrata/dev_to_ia_engineer/tree/main/modulos/02-prompting/reto/solucion): el prompt corregido en `extraer-aviso.md` y el extractor con los cambios marcados. Se comprueba con `comprobar.py --solucion`:

```text
Reto del módulo 2 · reto/solucion/extractor.py · rol chat_grande · 156 s
   OK    servicio: al menos 14 de 15: 15 de 15
   OK    hora_inicio: al menos 14 de 15: 15 de 15
   OK    afecta_clientes: al menos 14 de 15: 14 de 15 (mal: 3)
   OK    severidad: al menos 10 de 15: 11 de 15 (mal: 3, 4, 7, 9)
   OK    avisos enteros correctos: al menos 10 de 15: 11 de 15
Reto superado: 5 de 5 criterios.
```

Los cambios, en el orden en que se encontraron:

- **El ejemplo mal etiquetado.** Uno de los dos ejemplos ponía "media" a unos clientes que no pueden pagar. El modelo copia lo que ve en los ejemplos (lección 02). Corregirlo no basta: el prompt tampoco decía qué es cada severidad. La solución da los criterios del equipo y un ejemplo de cada severidad, para que "crítica" no sea un extremo que el modelo evita.
- **Qué cubre cada servicio.** Sin decirlo, "los productos nuevos no aparecen en la búsqueda" puede ser del catálogo o de la búsqueda.
- **El formato de la hora, en el esquema.** El prompt pide `HH:MM`, y el esquema lo exige con un patrón: `Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")`. "lunes" y "6:00" dejan de ser posibles.
- **Un campo para razonar antes de decidir.** `motivo` va primero, con qué falla, a quién y si hay alternativa. Es lo que hacen los jueces del curso.
- **Otro modelo.** Con todo lo anterior, estas son las medidas de la máquina del curso:

| | Avisos correctos | Severidad bien |
| --- | --- | --- |
| Partida, 1,5B | 3 de 15 | 6 de 15 |
| Solución, 1,5B | 9 de 15 | 9 de 15 |
| Partida, 7B | 6 de 15 | 8 de 15 |
| Solución, 7B | 11 de 15 | 11 de 15 |

El prompt corregido triplica los avisos correctos del de 1,5B, pero la severidad se queda en 9 de 15: aplicar criterios es lo que más le cuesta a un modelo pequeño. El de 7B llega con el mismo prompt. Es lo mismo que midió la lección 4.06: una misma mejora del prompt rinde distinto con cada modelo, y por eso se mide con el modelo con el que se va a usar.

Las cuatro severidades que siguen mal con el 7B son reales: en la 7, una búsqueda caída para todos sale "alta" en lugar de "crítica". Con 15 correos no compensa seguir retocando el prompt para arreglarlas. Lo siguiente sería tener más correos, para saber si la mejora se sostiene.

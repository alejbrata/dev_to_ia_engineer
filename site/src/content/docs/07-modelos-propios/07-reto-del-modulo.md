---
title: "Reto del módulo: ¿compensa el ajuste?"
description: "Reto del módulo 7, sin solución guiada: un ajuste que parece mejorar de forma significativa hasta que se encuentran las preguntas de la eval que estaban en los datos de entrenamiento"
---

Tienes un script con fallos, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio: ábrela al final, para comparar.

## Objetivos

- Detectar una fuga de datos (*data leakage*): casos de la eval que también están en el entrenamiento.
- Normalizar texto para que dos copias de la misma pregunta cuenten como la misma.
- Repetir una comparación sin los casos contaminados y decidir con lo que queda.

## El reto

Un compañero ha ajustado con LoRA el modelo pequeño, como en la lección 05, y trae los resultados. En las 40 preguntas de la eval, el base acierta 26 y el ajustado 33. Caso a caso, gana 8 y pierde 1, y la prueba de McNemar da p = 0,039. Propone ajustar.

Antes de decidir, hay que mirar una cosa que la lección 05 cuidaba al preparar los datos: si alguna pregunta de la eval estaba también en el entrenamiento. Un modelo que vio la pregunta al entrenar puede acertarla de memoria, y entonces acertarla no dice nada de lo que ha aprendido. Es el *data leakage* del machine learning clásico, y en un ajuste de LLM pasa con facilidad: los datos de entrenamiento salen de los mismos documentos que la eval, o de una exportación que ya la incluía.

Los datos están en la carpeta del reto:

- `eval.jsonl`: las 40 preguntas, que son preguntas con respuesta del dataset del módulo 4.
- `entrenamiento.jsonl`: las 162 preguntas con las que se ajustó.
- `resultados.jsonl`: si el base y el ajustado aciertan cada una.

Los resultados son simulados para el reto, pero se comportan como los de la lección 06.

[`reto/fuga.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/07-modelos-propios/reto/fuga.py) busca las preguntas solapadas y repite la comparación sin ellas:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/07-modelos-propios/reto/fuga.py
```

```text
5 preguntas de la eval están en el entrenamiento: ['m3-20', 'n-03', 'n-04', 'n-10', 'n-14']
todas              40 casos · base 26 · ajustado 33 · gana 8, pierde 1, p = 0.039
sin las solapadas  40 casos · base 26 · ajustado 33 · gana 8, pierde 1, p = 0.039
decisión: ajustar
```

Encuentra 5 solapadas, y aun así la comparación sin ellas sigue teniendo 40 casos. Arréglalo, y cambia `DECISION` por la que apoyen los datos. No cambies los ficheros de datos.

## Criterios de aceptación

1. "¿Qué es X?" y "que es x" se normalizan igual.
2. Encuentra las 12 preguntas de la eval que están en el entrenamiento.
3. No marca como solapada ninguna que no lo esté.
4. La comparación sin las solapadas no las cuenta.
5. Sin las solapadas, la diferencia entre base y ajustado deja de ser significativa.
6. `DECISION` es la que apoyan los datos.

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/07-modelos-propios/reto/comprobar.py) usa los datos del reto. No llama a ningún modelo. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/07-modelos-propios/reto/comprobar.py
```

```text
Reto del módulo 7 · reto/fuga.py
   FALLA «¿Qué es X?» y «que es x» son la misma pregunta: devuelve False, se esperaba True
   FALLA encuentra las 12 preguntas de la eval que están en el entrenamiento: encuentra 5
   OK    no marca como solapada ninguna que no lo esté
   FALLA la comparación sin las solapadas no las cuenta: devuelve 40, se esperaba 35
   FALLA sin las solapadas, la diferencia no es significativa: 40 casos: gana 8, pierde 1, p = 0.039
   FALLA la decisión es la que apoyan los datos: devuelve 'ajustar'
1 de 6 criterios. Sigue: lee el primero que falla.
```

El criterio 3 está para que la salida fácil no valga: marcar como solapada cualquier pregunta que se parezca un poco dejaría la eval sin casos. El reto está superado cuando dice `Reto superado: 6 de 6 criterios.`.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: las que no encuentra</summary>

Busca en `entrenamiento.jsonl` el principio de alguna pregunta de la eval, por ejemplo "Cuánto duró la caída de pagos". ¿Está igual que en `eval.jsonl`? ¿Qué le falta o le sobra?

</details>

<details>
<summary>Pista 2: normalizar</summary>

El módulo 6 ya normalizaba preguntas para la caché (`asistente.normalizar`): minúsculas, sin tildes y sin espacios de más. Aquí también sobran los signos de puntuación.

</details>

<details>
<summary>Pista 3: la comparación</summary>

Lee `comparar` línea a línea. ¿Dónde se usa `excluir`?

</details>

## La solución

Está en [`reto/solucion/fuga.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/07-modelos-propios/reto/solucion/fuga.py), con los tres cambios marcados, y se comprueba con `comprobar.py --solucion`:

```text
12 preguntas de la eval están en el entrenamiento: ['m3-12', 'm3-13', 'm3-20', 'm3-21', 'm3-26', 'n-03', 'n-04', 'n-05', 'n-07', 'n-10', 'n-13', 'n-14']
todas              40 casos · base 26 · ajustado 33 · gana 8, pierde 1, p = 0.039
sin las solapadas  28 casos · base 19 · ajustado 21 · gana 3, pierde 1, p = 0.625
decisión: no ajustar
```

Las copias que el código de partida no veía son estas, con la pregunta de la eval primero:

```text
m3-12 | ¿Cuánto duró la caída de pagos de marzo de 2026? | 'Cuánto duró la caída de pagos de marzo de 2026?'
m3-13 | ¿A partir de qué porcentaje de uso de disco salta la alerta de la búsqueda? | '¿A PARTIR DE QUÉ PORCENTAJE DE USO DE DISCO SALTA LA ALERTA DE LA BÚSQUEDA?'
m3-21 | ¿Cuándo salta la alerta PagosLatenciaP95Alta? | '¿Cuando salta la alerta PagosLatenciaP95Alta?'
n-05 | ¿Qué disponibilidad tenemos comprometida para el servicio de búsqueda? | '  ¿Qué  disponibilidad  tenemos  comprometida  para  el  servicio  de  búsqueda? '
```

Para el modelo, cada una es la misma pregunta. Para un `strip()`, no.

El ajustado acierta las 12 solapadas, y el base, 7. Ahí estaba casi toda su ventaja: de los 8 casos que ganaba, 5 eran preguntas que había visto al entrenar. Sin ellas gana 3 y pierde 1 en 28 casos, con p = 0,625. No hay mejora demostrada, y el ajuste tiene costes que el prompting y el RAG no tienen: entrenar, servir otro modelo y repetirlo cada vez que cambian los datos (lección 01). La decisión es no ajustar, la misma a la que llegó la lección 06 con datos limpios.

- **Una eval contaminada no da error: da una cifra mejor.** Por eso hay que buscar la fuga a propósito, antes de mirar los resultados.
- **Normalizar es lo mínimo.** Las 12 de este reto se encuentran con minúsculas, sin tildes, sin signos y sin espacios de más. Una paráfrasis ("¿Cuánto tiempo estuvo caído pagos en marzo?") no se encuentra así: para eso la lección 05 compara embeddings y descarta las preguntas de entrenamiento demasiado parecidas a alguna de la eval.
- **Un parámetro que no se usa es un fallo que no avisa.** `comparar` recibía `excluir` y lo ignoraba: la línea "sin las solapadas" imprimía lo mismo que "todas", y parecía que la fuga no cambiaba nada.

## Solución explicada paso a paso

:::caution[Contiene spoilers]
Abre estos apartados solo después de intentar el reto. Cada uno explica el fallo, el cambio que aparece en la solución de referencia y la lección que deja.
:::

<details>
<summary>Normalizar las preguntas antes de buscar contaminación</summary>

**Qué fallaba:** El original solo aplica `strip()`. Una misma pregunta con distinta capitalización, tildes o signos podría pasar desapercibida.

**Código original:**

```python
def normalizar(pregunta: str) -> str:
    return pregunta.strip()
```

**Código corregido:**

```python
import re
import unicodedata

def normalizar(pregunta: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", pregunta).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^\w\s]", " ", sin_tildes.lower()).split())
```

**Cómo se corrige:** La solución combina `unicodedata.normalize("NFKD", ...)`, eliminación de caracteres no alfanuméricos con `re.sub`, minúsculas y normalización de espacios.

**Qué aprendes:** Antes de celebrar una mejora de fine-tuning, comprueba que la evaluación no contiene ejemplos ya vistos. Esta normalización detecta variaciones superficiales, no paráfrasis.

</details>

<details>
<summary>Excluir realmente las preguntas filtradas</summary>

**Qué fallaba:** La función original recibe `excluir`, pero lo ignora al contar resultados.

**Código original:**

```python
def comparar(resultados: list[dict], excluir: set[str]) -> dict:
    ganados = sum(r["ajustado"] and not r["base"] for r in resultados)
    ...
```

**Código corregido:**

```python
def comparar(resultados: list[dict], excluir: set[str]) -> dict:
    resultados = [r for r in resultados if r["id"] not in excluir]
    ganados = sum(r["ajustado"] and not r["base"] for r in resultados)
    ...
```

**Cómo se corrige:** La solución añade `resultados = [r for r in resultados if r["id"] not in excluir]` antes de calcular aciertos, ganados, perdidos y p de McNemar.

**Qué aprendes:** Un análisis de sensibilidad que no cambia su población no es una comprobación válida.

</details>

<details>
<summary>Cambiar la decisión al analizar la eval sin fugas</summary>

**Qué fallaba:** La versión inicial fija `DECISION = "ajustar"` en función de las cifras contaminadas.

**Código original:**

```python
DECISION = "ajustar"
```

**Código corregido:**

```python
DECISION = "no ajustar"
```

**Cómo se corrige:** La solución marca `DECISION = "no ajustar"`: al excluir preguntas solapadas quedan 3 casos ganados y 1 perdido, p = 0,625.

**Qué aprendes:** Una ventaja aparente puede desaparecer tras eliminar contaminación. No demostrar mejora no significa demostrar igualdad: aquí no hay evidencia suficiente para justificar el ajuste y su coste.

</details>

**Comprobación:** ejecuta `uv run python modulos/07-modelos-propios/reto/comprobar.py` sobre tu código. Con `--solucion` se evalúa la implementación de referencia, no tus cambios.

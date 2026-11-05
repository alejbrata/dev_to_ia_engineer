---
title: "Reto del módulo: el juez que no sabe qué falta"
description: "Reto del módulo 4, sin solución guiada: construir un juez que detecte las respuestas que se dejan pasos de un procedimiento, calibrarlo con 20 casos etiquetados y comprobar con otros 10 que no se ha ajustado a ellos"
---

:::note[Revisado: 2026-11]
Las salidas son reales, con el modelo del rol `judge` (Qwen2.5 7B) en Ollama sobre CPU. Puedes usar el que quieras o puedas: el nombre está en `config/models.toml`.
:::

Tienes un juez con fallos, unos casos etiquetados, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio: ábrela al final, para comparar.

## Objetivos

- Construir un juez para una propiedad concreta y medir su acuerdo con etiquetas humanas (lección 04).
- Calibrarlo con unos casos y validarlo con otros que no has mirado, separados por procedimiento para que no se cuelen (lección 06).
- Reconocer cuándo la propia forma de preguntar al juez sesga su respuesta.

## El reto

El fallo que más repite el asistente de guardia es quedarse con una parte del procedimiento: dar el segundo paso sin el primero, o una rama de la condición sin la otra. En la lección 06 era la categoría "se queda con parte del procedimiento", y ninguno de los jueces del curso lo mide. El juez de fidelidad aprueba una respuesta incompleta, porque todo lo que dice está en el contexto.

[`reto/juez.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/reto/juez.py) intenta medirlo, con el prompt [`reto/juez-completa.md`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/reto/juez-completa.md). Tiene que aprobar las respuestas completas y rechazar las que se dejan algún paso. [`reto/casos.jsonl`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/reto/casos.jsonl) tiene 30 respuestas etiquetadas a mano sobre 12 procedimientos de los runbooks del módulo 3. Cada una lleva la pregunta, el procedimiento, la respuesta, si está completa y, si no, qué le falta. Una, sin el procedimiento:

```json
{"id": 17, "particion": "desarrollo", "procedimiento_id": "escalado",
 "pregunta": "¿Qué pasa si nadie de guardia confirma una alerta crítica?",
 "respuesta": "Si nadie confirma la alerta crítica en 30 minutos, se avisa al responsable del equipo.",
 "completa": false, "falta": "falta el escalón de los 15 minutos a la guardia secundaria"}
```

Están separadas en desarrollo (20 casos de 8 procedimientos) y prueba (10 casos de otros 4). Ningún procedimiento cae en los dos lados: si cayera, el juez podría "aprenderse" un procedimiento en desarrollo y acertarlo en prueba sin haber mejorado. Arregla el juez mirando solo desarrollo, y mira prueba al final. Puedes cambiar el prompt, el código y el rol, pero no los casos.

## Criterios de aceptación

1. Si el modelo no devuelve un JSON válido, el juez no aprueba la respuesta.
2. En desarrollo, el kappa con las etiquetas es de al menos 0,6.
3. En desarrollo, el juez detecta al menos el 75 % de las respuestas incompletas.
4. En prueba, el kappa es de al menos 0,5: el juez no se ha ajustado solo a desarrollo.

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/reto/comprobar.py) pasa tu juez por los 30 casos y mide el acuerdo con `curso_core.evals.acuerdo` (lección 04). Llama al modelo juez: de 3 a 10 minutos en la máquina del curso, según cuántas llamadas haga tu juez. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/reto/comprobar.py
```

```text
Reto del módulo 4 · reto/juez.py · rol judge · 175 s
   FALLA si el modelo no devuelve JSON, el juez no aprueba: devuelve True, se esperaba False
   FALLA desarrollo: kappa de al menos 0.6: 0.30 (acierta 13 de 20)
   FALLA desarrollo: detecta al menos el 75% de las incompletas: 7 de 11, y rechaza 3 completas
   FALLA prueba: kappa de al menos 0.5 (no se ha ajustado a desarrollo): 0.23 (acierta 6 de 10)
0 de 4 criterios. Sigue: lee el primero que falla.
```

Para ver los casos uno a uno, `juez.py` imprime el veredicto de cada caso de desarrollo junto a su etiqueta. El reto está superado cuando el comprobador dice `Reto superado: 4 de 4 criterios.`.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: qué ve el juez</summary>

Lee el prompt y la llamada: ¿qué información recibe el juez? ¿Podrías tú decir si a una respuesta le falta un paso sin ver el procedimiento? Y ¿qué pregunta le hace el prompt: si está completa, o otra cosa?

</details>

<details>
<summary>Pista 2: el veredicto</summary>

En la lección 04, el juez v2 dejaba de dar el veredicto él mismo: copiaba lo que encontraba y el código decidía. ¿Qué podría copiar este juez, y qué comprobaría el código?

</details>

<details>
<summary>Pista 3: si desarrollo pasa y prueba no</summary>

Mira qué pasos lista tu juez en los casos de prueba que falla. ¿Están todos los del procedimiento, o solo los que menciona la respuesta? Piensa en qué ve el juez en el momento de hacer la lista.

</details>

## La solución

Está en [`reto/solucion/`](https://github.com/alejbrata/dev_to_ia_engineer/tree/main/modulos/04-evals/reto/solucion): el juez, con los cambios marcados, y sus dos prompts. Se comprueba con `comprobar.py --solucion`:

```text
Reto del módulo 4 · reto/solucion/juez.py · rol judge · 506 s
   OK    si el modelo no devuelve JSON, el juez no aprueba
   OK    desarrollo: kappa de al menos 0.6: 0.90 (acierta 19 de 20)
   OK    desarrollo: detecta al menos el 75% de las incompletas: 10 de 11, y rechaza 0 completas
   OK    prueba: kappa de al menos 0.5 (no se ha ajustado a desarrollo): 0.78 (acierta 9 de 10)
Reto superado: 4 de 4 criterios.
```

Se llegó en dos versiones, y la primera es la parte más útil del reto.

**La primera versión** arreglaba lo evidente:

- le pasaba el procedimiento al juez;
- le preguntaba por la completitud, paso a paso;
- dejaba el veredicto al código, como el juez v2;
- no aprobaba cuando el JSON llegaba roto.

En desarrollo daba un kappa de 0,80, 18 de 20, sin rechazar ninguna respuesta completa. En prueba se quedaba en 0,23, 6 de 10: igual que el juez de partida.

**El fallo estaba en la forma de preguntar.** El juez veía la respuesta mientras hacía la lista de pasos, y apuntaba los que la respuesta mencionaba. En el caso 23 (diagnosticar por qué no salen los emails), la respuesta habla de los logs y de la cola de Redis, y el juez listó justo esos dos pasos. El del puerto 587, que es el que falta, no aparecía en su lista, así que todo lo listado estaba en la respuesta y la daba por completa. En desarrollo pasaba solo en 2 de 20 casos (el 14 y el 19), y dos fallos entre 20 no parecían un patrón. En prueba fueron 4 de 10.

**La segunda versión separa las dos tareas.** Una llamada saca los pasos del procedimiento sin ver la respuesta (`extraer-pasos.md`), y el código se queda solo con los que existen literalmente en el procedimiento. Otra llamada revisa cada paso numerado contra la respuesta (`juez-completa.md`). La respuesta está completa si el juez ha revisado cada paso y todos están. Cuesta el doble de llamadas, y por eso tarda 506 segundos frente a 175.

Lo que se lleva a cualquier juez:

- **Un juez que no tiene la referencia no puede saber qué falta.** Solo puede juzgar si la respuesta suena bien.
- **Si el modelo no da un veredicto válido, no se aprueba.** Un error que aprueba infla la métrica sin que nadie lo vea.
- **Lo que el juez ve al hacer una tarea sesga esa tarea.** Separa sacar la lista de juzgarla.
- **Para eso está prueba.** Desarrollo dio 0,80 a un juez que fuera de él era casi azar. Sin los 10 casos de prueba, separados por procedimiento, el juez habría llegado a producción con una cifra falsa.

## Solución explicada paso a paso

:::caution[Contiene spoilers]
Abre estos apartados solo después de intentar el reto. Cada uno explica el fallo, el cambio que aparece en la solución de referencia y la lección que deja.
:::

<details>
<summary>Sin el procedimiento no se puede juzgar qué falta</summary>

**Qué fallaba:** El juez original ve solo pregunta y respuesta; puede aprobar algo plausible aunque omita pasos del procedimiento.

**Código original:**

```python
mensajes = prompts.renderizar(
    prompt, pregunta=caso["pregunta"], respuesta=caso["respuesta"]
)
```

**Código corregido:**

```python
pasos = pasos_del_procedimiento(cliente, caso)
lista = "\n".join(f"{n}. {p}" for n, p in enumerate(pasos, 1))
mensajes = prompts.renderizar(
    prompt, pasos=lista, respuesta=caso["respuesta"]
)
```

**Cómo se corrige:** La solución primero carga `extraer-pasos.md` y extrae los pasos obligatorios a partir de `pregunta` y `procedimiento`, sin enseñar todavía la respuesta.

**Qué aprendes:** Para medir completitud se necesita una referencia independiente de la respuesta evaluada: si la referencia depende de la respuesta, reproduce sus omisiones.

</details>

<details>
<summary>No aprobar automáticamente cuando falla el juez</summary>

**Qué fallaba:** Antes, `except ErrorFormato: return True` convertía un fallo del evaluador en una aprobación.

**Código original:**

```python
except ErrorFormato:
    return True
```

**Código corregido:**

```python
except ErrorFormato:
    return False
```

**Cómo se corrige:** Después: `except ErrorFormato: return False`; si no se obtiene una lista válida de pasos tampoco se aprueba.

**Qué aprendes:** Un evaluador que falla de forma abierta infla artificialmente sus resultados. La política de fallo debe ser explícita y conservadora.

</details>

<details>
<summary>Verificar cada paso en vez de aceptar un sí/no</summary>

**Qué fallaba:** La versión inicial pide al modelo una conclusión global (`Veredicto.aprobada`).

**Código original:**

```python
class Veredicto(BaseModel):
    motivo: str
    aprobada: bool

return cliente.extraer(mensajes, Veredicto, rol=ROL,
                       opciones=OPCIONES)[0].aprobada
```

**Código corregido:**

```python
class Paso(BaseModel):
    numero: int
    en_la_respuesta: bool

class Revision(BaseModel):
    pasos: list[Paso]

revision = cliente.extraer(mensajes, Revision, rol=ROL,
                           opciones=OPCIONES)[0].pasos
incluidos = {r.numero: r.en_la_respuesta for r in revision}
return all(incluidos.get(n, False) for n in range(1, len(pasos) + 1))
```

**Cómo se corrige:** La solución utiliza `Revision` con una lista de `Paso(numero, en_la_respuesta)` y calcula `all(incluidos.get(n, False) for n in range(1, len(pasos) + 1))`.

**Qué aprendes:** Separar la identificación de criterios de la revisión de cada criterio hace más auditable el juez. El código, no una impresión general del LLM, toma la decisión final.

</details>

**Comprobación:** ejecuta `uv run python modulos/04-evals/reto/comprobar.py` sobre tu código. Con `--solucion` se evalúa la implementación de referencia, no tus cambios.

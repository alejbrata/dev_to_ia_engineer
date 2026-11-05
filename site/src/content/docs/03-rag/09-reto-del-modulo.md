---
title: "Reto del módulo: el RAG que no encuentra"
description: "Reto del módulo 3, sin solución guiada: una recuperación con tres fallos (troceado, lo que se indexa y un umbral sin medir) que hay que llevar a un recall@3 y un MRR mínimos sin pasarse de tokens de contexto"
---

:::note[Revisado: 2026-11]
Las salidas son reales, con el modelo de embeddings del rol `embeddings` (bge-m3) en Ollama sobre CPU. Puedes usar el que quieras o puedas: el nombre está en `config/models.toml`, y los umbrales pueden cambiar con otro modelo.
:::

Tienes un buscador con fallos, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio: ábrela al final, para comparar.

## Objetivos

- Encontrar en qué etapa de la recuperación se pierde un fragmento: al trocear, al indexar o al buscar.
- Medir cada cambio con recall@k, MRR y tokens de contexto, y no mejorar una métrica a costa de otra.
- Desconfiar de un umbral que nadie ha calibrado.

## El reto

[`reto/buscador.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/03-rag/reto/buscador.py) es la recuperación del asistente de documentación del módulo: trocea los documentos, los indexa con el modelo de embeddings y busca los 3 fragmentos más parecidos a cada pregunta. Son los mismos documentos y las mismas 26 preguntas con respuesta de las lecciones. Sus tres primeras búsquedas:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/03-rag/reto/buscador.py
```

```text
265 fragmentos indexados

¿Qué hago si pagos devuelve 'too many connections'?

¿Cuál es el límite del pool de conexiones de pagos?

¿Cada cuánto caduca el token de la API del banco?
   0.85 arquitectura-pagos:16: El token de la API del banco caduca cada 90 días. Su renovación está e
   0.82 runbook-pagos-credenciales:2: El token de la API del banco caduca cada 90 días. Si caduca, pagos rec
```

Dos de las tres preguntas se quedan sin contexto. El generador respondería "No aparece en la documentación" sobre un runbook que lo explica paso a paso. Arregla la recuperación. Puedes cambiar cómo se trocea, qué se indexa y cómo se busca, pero no el modelo de embeddings ni las preguntas.

## Criterios de aceptación

Con las 26 preguntas con respuesta:

1. Cada búsqueda devuelve 3 fragmentos.
2. El recall@3 es de al menos 0,80: en 21 preguntas o más, un fragmento con la evidencia está entre los 3 primeros.
3. El MRR es de al menos 0,65.
4. Como mucho 250 tokens de contexto por pregunta, de media.

El cuarto está para que la salida fácil no valga. Con trozos de 200 palabras, la lección 02 midió un recall@3 del 92 % y 467 tokens por pregunta: es pasarle al modelo media documentación en cada llamada, con su coste y sus distractores (lección 4.05).

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/03-rag/reto/comprobar.py) indexa con tu troceado, busca con tu función y mide como la lección 02. Solo usa el modelo de embeddings: menos de un minuto en la máquina del curso. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/03-rag/reto/comprobar.py
```

```text
Reto del módulo 3 · reto/buscador.py · 265 fragmentos · 28 s
   FALLA cada búsqueda devuelve 3 fragmentos: 26 de 26 preguntas con menos
   FALLA recall@3 de al menos 0.80: 0.08
   FALLA MRR de al menos 0.65: 0.08
   OK    como mucho 250 tokens de contexto por pregunta: 5
1 de 4 criterios. Sigue: lee el primero que falla.
```

El reto está superado cuando dice `Reto superado: 4 de 4 criterios.`.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: las búsquedas vacías</summary>

Imprime la puntuación de los 3 primeros resultados de varias preguntas, sin filtrar. ¿Entre qué valores se mueve la similitud de un fragmento que sí responde? ¿Y de dónde sale el umbral del código?

</details>

<details>
<summary>Pista 2: el troceado</summary>

Busca en `runbook-pagos-conexiones.md` la mitigación que responde a la primera pregunta ("Si hubo un despliegue reciente, vuelve a la versión anterior...") y mira cómo queda después de `trocear`: ¿en qué fragmento acaba, y qué tiene al lado? Mira las estrategias que comparó la lección 02.

</details>

<details>
<summary>Pista 3: lo que se indexa</summary>

Mira qué texto convierte el índice en embedding (`Fragmento.para_indexar`). Un fragmento cuyo texto es "1. Abre el panel de PgBouncer y mira el número de conexiones activas." ¿dice de qué servicio ni de qué problema habla?

</details>

## La solución

Está en [`reto/solucion/buscador.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/03-rag/reto/solucion/buscador.py), con los tres cambios marcados, y se comprueba con `comprobar.py --solucion`:

```text
Reto del módulo 3 · reto/solucion/buscador.py · 97 fragmentos · 25 s
   OK    cada búsqueda devuelve 3 fragmentos
   OK    recall@3 de al menos 0.80: 0.85
   OK    MRR de al menos 0.65: 0.72
   OK    como mucho 250 tokens de contexto por pregunta: 137
Reto superado: 4 de 4 criterios.
```

Cada arreglo, medido por separado en la máquina del curso:

| Cambio | recall@3 | MRR | Tokens |
| --- | --- | --- | --- |
| Código de partida | 0,08 | 0,08 | 5 |
| Sin el umbral de similitud | 0,65 | 0,53 | 85 |
| Por secciones, sin título | 0,77 | 0,62 | 129 |
| Por secciones, con título (solución) | 0,85 | 0,72 | 137 |

- **El umbral.** 0,75 parecía razonable, pero con bge-m3 un fragmento que responde puede quedarse en 0,6. Nadie lo había medido. Es el fallo que más pesa, y el más silencioso: la búsqueda no da error, devuelve una lista vacía. Si hace falta descartar fragmentos poco parecidos, el umbral se calibra con las preguntas, o se deja al reranker (lección 05).
- **El troceado.** Una línea suelta separa cada paso de su contexto y cada fila de una tabla de su cabecera. La sección de Markdown es la unidad que escribió el autor (lección 02), y aquí también la más barata en tokens de las que funcionan.
- **El título.** `trocear_por_secciones` pone en el título "documento > sección", y el índice lo convierte en embedding junto con el texto. Sin él, "Mitigación" no dice de qué servicio es. Son 8 centésimas de recall por una línea de contexto.

La solución llega al nivel de la lección 02, no más allá. Si quieres seguir, la búsqueda híbrida y el reranker (lecciones 04 y 05) son las siguientes palancas, y los criterios siguen valiendo para medirlas.

## Solución explicada paso a paso

:::caution[Contiene spoilers]
Abre estos apartados solo después de intentar el reto. Cada uno explica el fallo, el cambio que aparece en la solución de referencia y la lección que deja.
:::

<details>
<summary>Trocear por líneas rompe las unidades de significado</summary>

**Qué fallaba:** En `trocear()` cada línea se indexa aislada, dejando condiciones, pasos y tablas sin su contexto.

**Código original:**

```python
return [
    Fragmento(id=f"{doc}:{i}", doc=doc, titulo="", texto=linea.strip())
    for i, linea in enumerate(texto.splitlines())
    if linea.strip()
]
```

**Código corregido:**

```python
from curso_core.rag import trocear_por_secciones

return trocear_por_secciones(doc, texto)
```

**Cómo se corrige:** Antes: `Fragmento(..., titulo="", texto=linea.strip())` por cada línea. Después: `return trocear_por_secciones(doc, texto)` (importándolo desde `curso_core.rag`).

**Qué aprendes:** Un chunk debe conservar suficiente contexto para contestar; el tamaño mínimo no siempre mejora la recuperación.

</details>

<details>
<summary>El título del fragmento aporta información al embedding</summary>

**Qué fallaba:** El original pone `titulo=""`: un apartado llamado «Mitigación» puede no indicar a qué sistema se refiere.

**Código original:**

```python
Fragmento(id=f"{doc}:{i}", doc=doc, titulo="", texto=linea.strip())
```

**Código corregido:**

```python
# trocear_por_secciones() prepara fragmentos con el
# título del documento y de la sección.
return trocear_por_secciones(doc, texto)
```

**Cómo se corrige:** `trocear_por_secciones()` conserva títulos de documento y sección, que `Fragmento.para_indexar` incorpora al texto embebido.

**Qué aprendes:** En RAG importa *qué* se indexa, no solo cuántos fragmentos se generan.

</details>

<details>
<summary>Un umbral de similitud sin calibración descarta resultados útiles</summary>

**Qué fallaba:** El original filtra `r.puntuacion >= 0.75`. Un fragmento relevante puede quedar por debajo de ese umbral con este modelo.

**Código original:**

```python
SIMILITUD_MINIMA = 0.75
return [r for r in indice.buscar(pregunta, k)
        if r.puntuacion >= SIMILITUD_MINIMA]
```

**Código corregido:**

```python
return indice.buscar(pregunta, k)
```

**Cómo se corrige:** Antes: `return [r for r in indice.buscar(pregunta, k) if r.puntuacion >= SIMILITUD_MINIMA]`. Después: `return indice.buscar(pregunta, k)`.

**Qué aprendes:** Calibra umbrales con preguntas representativas o utiliza reranking; una cifra arbitraria puede eliminar el contexto que la generación necesita.

</details>

**Comprobación:** ejecuta `uv run python modulos/03-rag/reto/comprobar.py` sobre tu código. Con `--solucion` se evalúa la implementación de referencia, no tus cambios.

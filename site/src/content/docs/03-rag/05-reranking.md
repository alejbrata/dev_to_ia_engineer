---
title: "Reranking"
description: "Reordenar los candidatos de la búsqueda con un cross-encoder: cuánto mejora el orden, cuánto cuesta en latencia y qué no arregla"
---

:::note[Revisado: 2026-10]
Las salidas son reales, con el reranker bge-reranker-v2-m3 (GGUF Q8_0) en `llama-server` de llama.cpp, sobre CPU, y bge-m3 en Ollama para la búsqueda. Puedes usar otro reranker: cambia el rol `reranker` en `config/models.toml` y vuelve a medir.
:::

## Objetivos

Al terminar esta lección podrás:

- Explicar la diferencia entre un bi-encoder (embeddings) y un cross-encoder (reranker).
- Servir un reranker en local y llamarlo con el formato `/rerank`.
- Medir cuánto mejora el reranking el recall y el MRR, y cuánta latencia añade.
- Elegir cuántos candidatos reordenar con datos, no a ojo.
- Explicar por qué una puntuación de relevancia alta no garantiza que el fragmento tenga la respuesta.

## Teoría

### Dos formas de comparar una pregunta con un texto

Un modelo de embeddings es un **bi-encoder**: convierte la pregunta y cada fragmento en vectores **por separado**, y luego compara los vectores. Como los vectores de los fragmentos se calculan una vez y se guardan, buscar entre millones es barato. El precio es que el modelo nunca ve la pregunta y el fragmento juntos.

Un reranker es un **cross-encoder**: recibe la pregunta y el fragmento **a la vez**, en la misma entrada, y devuelve una puntuación de relevancia. Puede fijarse en qué parte del fragmento responde a qué parte de la pregunta. Puntúa mejor, pero no hay nada que precalcular: cada par pregunta-fragmento es una pasada del modelo.

De ahí el diseño habitual en dos etapas: la búsqueda (densa, léxica o híbrida) trae unos pocos candidatos de forma barata, y el reranker solo reordena esos candidatos. Es la misma idea que un `WHERE` con índice seguido de una ordenación cara sobre las filas que quedan.

### Servir el reranker

No hace falta instalar nada nuevo en Python. `llama-server`, el de la lección 02 del módulo 1, puede servir un reranker con la opción `--reranking`, y expone un endpoint `/v1/rerank`. El formato (una consulta y una lista de documentos; un índice y una puntuación por documento) es el que usan también vLLM y las APIs de rerank de Jina o Cohere, así que cambiar de servidor es cambiar `config/models.toml`.

`ClienteLLM.reordenar(consulta, documentos)` hace la llamada, con reintentos y traza como el resto. `curso_core.rag.IndiceReordenado` envuelve cualquier índice: le pide 20 candidatos, los reordena y devuelve los k primeros.

### Qué significa la puntuación

bge-reranker-v2-m3 devuelve un número sin escala fija (un *logit*): positivo, la considera relevante; muy negativo, no. Si necesitas algo entre 0 y 1, se aplica una sigmoide. Como con los embeddings, lo útil es el orden, y la escala solo vale para ese modelo.

## Práctica

Arranca el reranker en una terminal aparte. La primera vez descarga el modelo (636 MB):

```sh title="Terminal aparte · se queda en marcha"
llama-server -hf gpustack/bge-reranker-v2-m3-GGUF:Q8_0 --reranking --port 8082
```

Cuando veas `listening on http://127.0.0.1:8082`, lanza la práctica en la terminal de VS Code:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/03-rag/reranking.py
```

[`reranking.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/03-rag/reranking.py) mide la búsqueda densa y la híbrida con y sin reranking, prueba varios números de candidatos y compara las puntuaciones de las preguntas con y sin respuesta:

```text
1. Sin y con reranking de 20 candidatos, 26 preguntas con respuesta
   búsqueda                   recall@1  recall@3    MRR  ms/búsqueda
   densa                          62%       85%   0.72          108
   densa + reranking              73%       92%   0.82         1246
   híbrida                        58%       85%   0.71           79
   híbrida + reranking            73%       88%   0.81         1188

2. Densa + reranking, según cuántos candidatos se reordenan
    5 candidatos               73%       92%   0.82          404
   10 candidatos               73%       88%   0.81          678
   20 candidatos               73%       92%   0.82         1190
   40 candidatos               73%       92%   0.82         2284

3. Posición del primer fragmento con la respuesta (densa → densa + reranking)
    2 → 1   4. ¿Qué significa el error invalid_grant al iniciar sesión con Google?
    3 → 2   7. ¿Cuál es la disponibilidad comprometida del servicio de notificaciones?
    - → 2  11. ¿Cuál fue la causa de la caída de pagos de marzo de 2026?
    3 → -  15. La tienda está enseñando precios viejos. ¿Qué hago?
    - → 1  19. Si perdemos el índice de búsqueda, ¿cuánto se tarda en reconstruirlo?
    2 → 1  20. Se ha filtrado una clave de API en un repositorio. ¿Qué hago?
    - → 3  24. Desde anoche no llega ningún aviso a los móviles de los clientes. ¿Qué puede estar pasando?

4. Puntuación del primer resultado tras el reranking
   con respuesta  -1.13 a   8.07 · sin respuesta  -7.18 a   1.61
   umbral  -4.0: descarta 0 de 26 con respuesta, deja pasar 1 de 4 sin respuesta
   umbral  -2.0: descarta 0 de 26 con respuesta, deja pasar 1 de 4 sin respuesta
   umbral   0.0: descarta 3 de 26 con respuesta, deja pasar 1 de 4 sin respuesta
```

## Mide y depura

### Mejora el orden, y se nota

Es la primera técnica del módulo que mejora claramente a la búsqueda densa: el recall@1 pasa del 62 % al 73 %, el recall@3 del 85 % al 92 % y el MRR de 0,72 a 0,82. La parte 3 enseña de dónde sale: seis preguntas suben, tres de ellas desde fuera del top 3 (la 11, la 19 y la 24). La 11 es la del postmortem de marzo que en la lección 04 solo encontraba BM25.

No todo sube. La pregunta 15 ("la tienda está enseñando precios viejos") sale del top 3: el reranker prefiere secciones del catálogo que hablan de precios, pero no la de mitigación, que es la que tiene la respuesta. Mira siempre las preguntas que empeoran, no solo la media.

Con reranking, la híbrida deja de aportar: los dos quedan en el 73 % de recall@1, y la densa con reranking queda algo mejor en recall@3. En este corpus, el reranker arregla el orden mejor que la fusión con BM25.

### Cuesta diez veces más

La búsqueda pasa de unos 100 ms a 1,2 s. En la parte 2 se ve que el coste crece con los candidatos: unos 55 ms por candidato en la CPU de la máquina del curso. Con GPU sería mucho menos, pero la proporción entre bi-encoder y cross-encoder no cambia: el reranker hace una pasada del modelo por candidato.

Para un asistente interno, 1,2 s antes de empezar a generar puede ser aceptable. Para un autocompletado, no. Decide con el presupuesto de latencia de tu caso, y mide el reranker por separado en tus trazas (rol `reranker`): es fácil que sea el paso más lento antes de la generación.

### Más candidatos no siempre es mejor

Con 5 candidatos se consigue lo mismo que con 20 o 40, en un tercio del tiempo. Y con 10 sale peor que con 5. No es ruido: el resultado se repite en cada ejecución. Al pasar de 5 a 10, entra un candidato (la sección de diagnóstico del runbook de pagos) que el reranker coloca por delante de la sección con la respuesta de la pregunta 1, y la saca del top 3. Al pasar a 20, esa pregunta sigue perdida, pero entra la respuesta de la 24, que no estaba entre los 10 primeros de la búsqueda densa. Una cosa compensa la otra.

Cada candidato que añades es una oportunidad de encontrar la respuesta y otra de colar un distractor. La única forma de saber qué número te compensa es medirlo con tus preguntas, como en la parte 2.

### Variaciones pequeñas entre llamadas

Si llamas dos veces al reranker con los mismos textos, las puntuaciones pueden cambiar en las centésimas (por ejemplo, -0,931 y -0,914 para el mismo par). `llama-server` procesa varios documentos a la vez en el mismo lote, y el resultado numérico depende ligeramente de con qué otros documentos comparte el lote. Aquí el orden no cambió en ninguna prueba, pero si dos candidatos quedan casi empatados, el orden puede variar entre ejecuciones. Es la misma idea que el no determinismo del módulo 1: tenlo en cuenta antes de escribir un test que compare puntuaciones exactas.

## Errores frecuentes

**Reordenar demasiados candidatos.** La latencia crece con cada uno, y la calidad no siempre. Empieza con pocos y sube solo si la medida lo justifica.

**Reordenar con un texto distinto del que se indexó.** `IndiceReordenado` manda el fragmento con su título (`para_indexar`), igual que se indexó. Si mandas solo el texto, el reranker pierde el contexto del título.

**Usar el reranker sin mirar su licencia.** Hay rerankers populares con licencias no comerciales. bge-reranker-v2-m3 es Apache 2.0; comprueba la del tuyo antes de llevarlo a producción.

**Tratar la puntuación como una probabilidad.** Es un logit sin escala fija, y otro modelo dará otra escala.

### Anatomía de un error: la sección relevante que no tiene la respuesta

La parte 4 parece una buena noticia: con un umbral de -2,0 no se pierde ninguna pregunta con respuesta y solo pasa una de las cuatro que no la tienen. Es mejor que el umbral sobre la similitud de la lección 04. Pero mira la que se cuela:

```text
30. ¿Quién es el responsable del equipo Cobros?
    reranker: runbook-pagos-conexiones#3   1.61
    densa:    runbook-pagos-conexiones#3   0.596
```

**Cómo leerlo.** El primer resultado es la sección de escalado del runbook de pagos, con 1,61. Es una puntuación alta: siete de las 26 preguntas con respuesta tienen una puntuación más baja en su primer resultado. Para el reranker, este fragmento es muy relevante.

**Causa.** Y lo es. La sección dice: "Si en 15 minutos los cobros no se recuperan, escala al responsable del equipo Cobros." Habla exactamente de lo que pregunta la pregunta. Pero no dice **quién** es el responsable. El reranker mide si un texto trata de lo que se pregunta, no si contiene la respuesta. Son cosas distintas, y en documentación real pasa a menudo: un procedimiento menciona un rol, una tabla o un sistema sin dar el dato.

**Solución.** No uses la puntuación de recuperación, ni siquiera la del reranker, para decidir que hay respuesta. Úsala como señal en las trazas. La decisión se toma en la generación: el modelo tiene que poder citar el fragmento que contiene el dato y abstenerse si no lo encuentra. Y lo que dice el modelo hay que comprobarlo midiendo la fidelidad de la respuesta al contexto. Es la lección 06.

## Bitácora

TODO(alex)

## Para profundizar

- Nogueira y Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085) (2019). El origen del reranking con cross-encoders.
- [Ficha de bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) en Hugging Face, con su licencia.
- [Reranking en llama-server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server), en la documentación del servidor de llama.cpp.
- [Retrieve & Re-Rank](https://www.sbert.net/examples/applications/retrieve_rerank/README.html), en la documentación de Sentence Transformers: bi-encoders frente a cross-encoders.

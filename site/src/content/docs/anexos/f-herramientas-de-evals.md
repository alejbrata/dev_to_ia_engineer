---
title: "F. Herramientas de evals"
description: "Herramientas de evals: Ragas, DeepEval, promptfoo e Inspect frente a lo construido en el módulo 4"
---

:::note[Revisado: 2026-10]
Este anexo compara las herramientas a partir de su documentación oficial (enlazada en cada apartado). No se han ejecutado en el curso: las cifras y salidas reales del curso son las del módulo 4. Estas herramientas cambian rápido; comprueba la documentación antes de adoptar una.
:::

En el módulo 4 las evals se construyen a mano, sobre `curso_core.evals`: un dataset anclado, comprobadores deterministas, un juez calibrado, comparación caso a caso y un control en CI. Se hizo así para que entiendas cada pieza. En un proyecto real puede compensar usar una herramienta. Este anexo te ayuda a elegir, traduciendo cada herramienta a lo que ya conoces.

## Qué aporta una herramienta y qué no

Lo que el módulo 4 construyó, y una herramienta te puede dar hecho:

- **Ejecutar un dataset contra un sistema** y guardar el resultado caso a caso (`Informe`).
- **Métricas ya escritas**: fidelidad, recall de contexto, relevancia de la respuesta… (lecciones 03 y 05).
- **Jueces con prompts ya escritos** (lección 04).
- **Un visor** de resultados, más cómodo que leer un JSONL.
- **Integración con CI** (lección 07).

Lo que ninguna te da hecho, y es lo que más pesa en la calidad de la eval:

- **El dataset anclado a tu corpus** (lección 02). Sin él, cualquier métrica mide poco.
- **La calibración del juez** contra etiquetas tuyas (lección 04). Que una herramienta traiga una métrica de fidelidad no dice cuánto se equivoca con tus datos.
- **El análisis de errores** (lección 06). Leer los fallos es trabajo tuyo.
- **Las reglas de regresión** (lección 07): qué casos son críticos y qué cuenta como empeorar.

Si adoptas una herramienta, sigue haciendo esas cuatro cosas. Y valida sus métricas igual que el juez de la lección 04: contra tus etiquetas, con sensibilidad, especificidad y kappa.

## Ragas

[Ragas](https://docs.ragas.io/en/stable/) es una librería de Python centrada en evaluar RAG. Se instala con `pip install ragas` (o `uv add ragas`).

- **Métricas de RAG**: Context Precision, Context Recall, Context Entities Recall, Noise Sensitivity, Response Relevancy y Faithfulness, más variantes multimodales ([lista de métricas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)).
- **Faithfulness** no necesita respuesta de referencia: usa la pregunta, la respuesta y los contextos recuperados. Es la fidelidad de la lección 04 (un modelo divide la respuesta en afirmaciones y comprueba cada una).
- **Context Recall** sí necesita una referencia. Es el recall de la lección 05, pero calculado con un modelo sobre una respuesta de referencia, no sobre segmentos anclados.
- **Métricas sin modelo**: tiene variantes que no usan LLM, como un recall de contexto no basado en modelo.
- **Juez configurable**: acepta cualquier modelo con API compatible con OpenAI, también Ollama en local (`base_url="http://localhost:11434/v1"`), según su [guía de inicio](https://docs.ragas.io/en/stable/getstarted/quickstart/).

**Equivalencia con el curso.** Faithfulness ≈ el juez v2 de la lección 04, pero sin la comprobación literal de las citas con código. Context Recall ≈ `dataset.relevante`, pero con un modelo en lugar de un segmento literal.

**Cuándo encaja.** Si tu sistema es un RAG y quieres métricas estándar con nombres que el resto del sector reconoce. Calibra su Faithfulness con tus etiquetas antes de fiarte del número: es un juez, con los mismos fallos que viste en la lección 04.

## DeepEval

[DeepEval](https://deepeval.com/docs/getting-started) es un framework de Python con estilo de tests. Se instala con `pip install -U deepeval`.

- **Tests como pytest**: escribes funciones `test_...` con un `LLMTestCase` y llamas a `assert_test(caso, [métricas])`. Se ejecutan con `deepeval test run test_fichero.py`, que se integra con pytest.
- **Métricas de RAG**: Answer Relevancy, Faithfulness, Contextual Relevancy, Contextual Recall y Contextual Precision ([introducción a las métricas](https://deepeval.com/docs/metrics-introduction)). Contextual Recall necesita referencia.
- **G-Eval**: un juez a partir de criterios escritos en lenguaje natural. Primero genera los pasos de evaluación y después puntúa de 0 a 1, con un umbral (0,5 por defecto).
- **Juez**: los ejemplos usan OpenAI por defecto (necesitan `OPENAI_API_KEY`). Admite Ollama (`deepeval set-ollama --model=<modelo>`), con el aviso de que un modelo propio tiene que devolver JSON válido y seguir bien las instrucciones. Con el modelo de 1,5B del curso, ya viste en la lección 04 que no basta.
- **Plataforma**: todo corre en local. Enviar resultados a su plataforma (Confident AI) es opcional y requiere iniciar sesión.

**Equivalencia con el curso.** `assert_test` con un umbral ≈ un test de pytest sobre `puntuar`. G-Eval ≈ el juez v1 de la lección 04: el modelo decide solo, sin que el código compruebe nada.

**Cuándo encaja.** Si tu equipo ya piensa en tests de pytest y quiere evals con la misma forma. Cuidado con los umbrales por caso: con jueces que se equivocan un 10-20 % de las veces, un test que falla puede ser el juez, no el sistema.

## promptfoo

[promptfoo](https://www.promptfoo.dev/docs/intro/) es una herramienta de línea de comandos (Node.js) que define las evals en YAML. Se instala con `npm install -g promptfoo` o se usa con `npx promptfoo@latest`, y necesita Node.js 22.22 o superior ([instalación](https://www.promptfoo.dev/docs/installation/)). Corre en local y habla directamente con el proveedor del modelo.

- **Configuración**: en YAML defines prompts, proveedores y casos (`tests`), y en cada caso, `vars` (las variables) y `assert` (las comprobaciones).
- **Comprobaciones deterministas**: `equals`, `contains`, `icontains`, `regex`, `is-json`, `contains-json`, `latency`, `cost` y más, y cualquiera se puede negar con el prefijo `not-` ([comprobaciones](https://www.promptfoo.dev/docs/configuration/expected-outputs/)).
- **Código propio**: comprobaciones `python` o `javascript`, en línea o en un fichero.
- **Comprobaciones con modelo**: `llm-rubric`, `g-eval`, `similar` (embeddings), `context-faithfulness`, `context-recall`, `answer-relevance`, `factuality` y más.
- **Pesos y umbrales**: cada comprobación tiene un peso y cada caso, un umbral sobre la puntuación combinada.
- **Puntuar salidas guardadas**: `promptfoo eval --assertions asserts.yaml --model-outputs outputs.json` aplica las comprobaciones a salidas ya generadas. Es la idea de `--grabadas` del módulo 4.
- **CI**: tiene una GitHub Action y está pensada para CI/CD.

**Equivalencia con el curso.** `contains` / `icontains` ≈ `contiene_subcadena`. Una comprobación `python` ≈ cualquiera de los comprobadores de `dataset.py`, incluido el `contiene` con límites de palabra de la lección 03. `not-contains` ≈ lo prohibido en los guardarraíles.

**Cuándo encaja.** Para comparar prompts y proveedores rápidamente, sobre todo si quien mantiene las evals prefiere YAML a Python. Es la que más se parece al flujo del módulo 2 (variantes de prompt contra los mismos casos).

## Inspect

[Inspect](https://inspect.aisi.org.uk/) es un framework de Python del UK AI Security Institute. Se instala con `pip install inspect-ai`.

- **Tarea**: una evaluación es una `Task` que junta tres piezas: un dataset (muestras con `input` y `target`), un solver (lo que produce la respuesta) y un scorer (lo que la puntúa).
- **Solvers**: desde `generate()`, que solo llama al modelo, hasta agentes con herramientas (`react()`). Es la más preparada para evaluar agentes (lección 5.08).
- **Scorers**: de cadena (`includes()`) y con modelo (`model_graded_qa()`), y puedes escribir los tuyos.
- **Ejecución**: `inspect eval fichero.py --model <proveedor>/<modelo>`, y `inspect view` abre un visor de los registros.
- **Proveedores**: más de 20, incluidos Ollama, vLLM y llama-cpp-python en local, y cualquier API compatible con OpenAI (`openai-api/<proveedor>/<modelo>`) ([proveedores](https://inspect.aisi.org.uk/providers.html)).

**Equivalencia con el curso.** Dataset ≈ `casos.jsonl`. Solver ≈ `sistema.responder`. Scorer ≈ `dataset.puntuar` o el juez. El registro que guarda ≈ el `Informe` en JSONL.

**Cuándo encaja.** Para evaluaciones con agentes, herramientas y muchas muestras, o si necesitas reproducibilidad y un visor serio. Es la más completa de las cuatro y también la que más estructura impone.

## Cómo elegir

| Necesitas… | Mira primero |
| --- | --- |
| Métricas estándar de RAG con nombres reconocibles | Ragas |
| Evals con forma de tests de pytest | DeepEval |
| Comparar prompts y proveedores con configuración en YAML | promptfoo |
| Evaluar agentes con herramientas, con un visor de registros | Inspect |
| Entender qué mide cada cosa y controlar cada detalle | Lo del módulo 4 |

No son excluyentes. Un patrón razonable es mantener tu dataset anclado y tus reglas de regresión en tu código, y usar una herramienta para las métricas con modelo o para el visor. Si cambias de herramienta, el dataset y las etiquetas siguen sirviendo: son lo que más cuesta construir.

## Errores frecuentes

**Adoptar la métrica de fidelidad de una herramienta sin calibrarla.** Es un juez. Mídela contra tus etiquetas antes de usarla para decidir.

**Usar como juez el modelo que viene por defecto sin saberlo.** Algunas herramientas usan un proveedor comercial por defecto. Revisa qué modelo juzga, cuánto cuesta y adónde van tus datos.

**Comparar números entre herramientas.** "Faithfulness 0,82" en una y "0,82" en otra no son lo mismo: cambian el prompt del juez, el modelo y la forma de agregar. Compara versiones de tu sistema con la misma herramienta y la misma configuración.

**Creer que la herramienta sustituye al dataset.** Una herramienta ejecuta y puntúa. Qué preguntas hacer, anclarlas al corpus y decidir qué es un acierto sigue siendo trabajo tuyo.

## Para profundizar

- [Documentación de Ragas](https://docs.ragas.io/en/stable/)
- [Documentación de DeepEval](https://deepeval.com/docs/getting-started)
- [Documentación de promptfoo](https://www.promptfoo.dev/docs/intro/)
- [Documentación de Inspect](https://inspect.aisi.org.uk/)
- Es et al., [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217) (2023).
- Liu et al., [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://arxiv.org/abs/2303.16634) (2023).

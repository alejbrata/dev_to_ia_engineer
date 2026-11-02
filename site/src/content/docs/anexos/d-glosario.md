---
title: "D. Glosario"
description: "Los términos del curso, con una definición corta y la lección donde se explican"
---

Los términos técnicos que usa el curso, ordenados alfabéticamente. Cada definición es corta a propósito: la explicación completa, con su práctica, está en la lección que se enlaza.

## A

**Abstención**. Que el sistema diga que no sabe en lugar de inventar. En el asistente del curso, responder exactamente "No aparece en la documentación". Se mide aparte: abstenerse cuando había respuesta también es un fallo. → [Cuándo usar RAG (y cuándo no)](../../03-rag/01-cuando-usar-rag/)

**Agente**. Sistema en el que el modelo decide qué hacer a continuación (qué herramienta llamar, cuándo parar) en un bucle, en lugar de seguir pasos fijados en el código. Ver también *workflow*. → [Workflow frente a agente](../../05-agentes/01-workflow-frente-a-agente/)

**Análisis de errores**. Leer los fallos de una eval y clasificarlos por causa antes de cambiar nada. Es lo que decide qué mejora probar. → [Análisis de errores](../../04-evals/06-analisis-de-errores/)

**Anclaje**. En un dataset de evaluación, ligar cada caso al fragmento de los datos que contiene su respuesta. Permite saber si un fallo es de la búsqueda o de la generación. → [Datasets de referencia](../../04-evals/02-datasets-de-referencia/)

**API compatible con OpenAI**. El formato de la API de chat de OpenAI, que han adoptado muchos servidores (Ollama, llama.cpp, vLLM). Cambiar de uno a otro es cambiar la URL. → [APIs y SDKs](../../01-fundamentos-de-llms/04-apis-y-sdks/)

## B

**Batching continuo**. Técnica de los servidores de inferencia: generar el siguiente token de varias peticiones a la vez, aprovechando cada lectura de los pesos. Sube el rendimiento total a costa de la latencia de cada petición. → [Inferencia local (Ollama, llama.cpp, vLLM)](../../07-modelos-propios/03-inferencia-local/)

**bfloat16**. Formato de coma flotante de 16 bits muy usado para guardar pesos. Ocupa la mitad que float32; en CPUs sin soporte específico puede ser más lento. → [Modelos abiertos](../../07-modelos-propios/02-modelos-abiertos/)

**BM25**. Búsqueda clásica por palabras clave, ponderada por su frecuencia. Funciona bien con identificadores y términos exactos; combinada con la densa da la búsqueda híbrida. → [Recuperación](../../03-rag/04-recuperacion/)

## C

**Caché de respuestas**. Guardar respuestas para no volver a llamar al modelo con la misma pregunta. En el curso, la clave incluye la huella del sistema para que un cambio la invalide. → [Arquitectura](../../06-produccion/01-arquitectura/)

**Caché KV**. Las claves y valores de atención de los tokens ya procesados, que el modelo guarda para no recalcularlos. Crece con el contexto y con las peticiones simultáneas. → [Modelos abiertos](../../07-modelos-propios/02-modelos-abiertos/)

**Chunking**. Trocear los documentos en fragmentos para indexarlos y recuperarlos. Cómo se trocea cambia lo que encuentra la búsqueda. → [Ingesta y chunking](../../03-rag/02-ingesta-y-chunking/)

**Citas**. Indicar de qué fragmento sale cada afirmación de la respuesta. Permite comprobar la fidelidad y que el usuario vaya a la fuente. → [Generación con citas](../../03-rag/06-generacion-con-citas/)

**Contexto (ventana de)**. El número máximo de tokens que el modelo procesa a la vez: el prompt más la respuesta. Lo que no cabe se recorta o da error. → [Ventana de contexto y sus límites](../../01-fundamentos-de-llms/02-ventana-de-contexto/)

**Cuantización**. Guardar los pesos con menos bits (8, 4, 2...) para que ocupen menos y vayan más rápido, a cambio de algo de precisión. Se mide con la eval de la tarea. → [Cuantización](../../07-modelos-propios/04-cuantizacion/)

## D

**Decoder, encoder y encoder-decoder**. Las tres arquitecturas de transformer. Los LLMs de chat son decoders (generan texto); los encoders representan texto (clasificar, embeddings); los encoder-decoder transforman un texto en otro (traducir). → [B.2 Encoder, decoder y encoder-decoder](../b2-encoder-decoder-y-encoder-decoder/)

**Destilación**. Entrenar un modelo pequeño (alumno) con las respuestas de uno grande (maestro) para que se comporte como él en una tarea. → [Fine-tuning con LoRA/QLoRA](../../07-modelos-propios/05-fine-tuning-con-lora-qlora/)

## E

**Embedding**. Vector de números que representa el significado de un texto. Textos parecidos tienen vectores cercanos: es la base de la búsqueda densa. → [Embeddings y bases vectoriales](../../03-rag/03-embeddings-y-bases-vectoriales/)

**Eval**. Conjunto de casos con su respuesta esperada y una forma de puntuar las respuestas del sistema. Es lo que permite saber si un cambio mejora o empeora. → [Por qué evaluar](../../04-evals/01-por-que-evaluar/)

## F

**Few-shot**. Incluir ejemplos resueltos en el prompt para mostrar al modelo qué se espera. → [Few-shot, técnicas y mitos](../../02-prompting/02-few-shot/)

**Fidelidad**. En RAG, que todo lo que afirma la respuesta esté apoyado por los fragmentos recuperados (en inglés, *faithfulness*). → [Evals de RAG](../../04-evals/05-evals-de-rag/)

**Fine-tuning (ajuste fino)**. Seguir entrenando un modelo con ejemplos de tu tarea, cambiando sus pesos. Sirve para el comportamiento, no para darle conocimiento que cambia. → [Prompting, RAG o fine-tuning](../../07-modelos-propios/01-prompting-rag-o-fine-tuning/)

## G

**GGUF**. Formato de llama.cpp que guarda en un solo fichero los pesos (normalmente cuantizados), el tokenizador, la plantilla de chat y los metadatos. Es el que usa Ollama. → [Modelos abiertos](../../07-modelos-propios/02-modelos-abiertos/)

**Grafo de estado**. Forma de organizar un agente o workflow como nodos (pasos) y aristas (transiciones) sobre un estado compartido, con puntos de control y aprobación humana. → [Grafos de estado desde cero](../../05-agentes/05-grafos-de-estado-desde-cero/)

**Graph of Thoughts**. Técnica de razonamiento en la que el modelo explora ideas como un grafo: las ramifica, las combina y las refina. Sucesora de chain-of-thought y tree-of-thoughts. → [C. Herramientas y estrategias de desarrollo con IA](../c-desarrollo-con-ia/)

**Guardrail**. Comprobación antes o después del modelo que bloquea entradas o salidas no permitidas: inyecciones, datos personales, formatos. Es un control en código, no una petición al modelo. → [Guardrails](../../06-produccion/05-guardrails/)

## H

**Huella**. En el curso, un resumen (hash) del contenido de los ficheros que pueden cambiar las respuestas del sistema. Si cambia, los resultados grabados de la eval ya no valen. → [Evals en CI](../../04-evals/07-evals-en-ci/)

## I

**Intervalo de confianza**. El rango en el que probablemente está el valor real de una métrica medida con pocos casos. El curso usa el intervalo de Wilson al 95 %. → [Métricas deterministas](../../04-evals/03-metricas-deterministas/)

**Inyección de prompt**. Texto que intenta que el modelo ignore sus instrucciones. Directa, si viene del usuario; indirecta, si llega dentro de un documento o una herramienta. → [Seguridad](../../06-produccion/04-seguridad/)

## L

**Latencia p50 y p95**. La mediana (p50) y el percentil 95 del tiempo de respuesta. El p95 es lo que esperan los usuarios con peor suerte. → [Métricas operativas](../../06-produccion/03-metricas-operativas/)

**Línea base**. Lo que da la solución más simple (sin LLM, o con un prompt sin más). Da sentido a cualquier resultado. → [Especificación](../../08-proyecto-final/01-especificacion/)

**LLM-as-judge**. Usar un modelo para puntuar las respuestas de otro cuando no hay una comprobación determinista. Hay que calibrarlo con etiquetas humanas. → [LLM-as-judge](../../04-evals/04-llm-as-judge/)

**Logprobs**. Las probabilidades (en logaritmo) que el modelo asigna a cada token generado y a sus alternativas. → [Cómo funciona un LLM](../../01-fundamentos-de-llms/01-como-funciona-un-llm/)

**LoRA y QLoRA**. Ajuste fino que congela el modelo y entrena solo dos matrices pequeñas por capa. QLoRA hace lo mismo con el modelo base cuantizado a 4 bits, para que quepa en menos memoria. → [Fine-tuning con LoRA/QLoRA](../../07-modelos-propios/05-fine-tuning-con-lora-qlora/)

## M

**McNemar (prueba de)**. Prueba estadística para comparar dos versiones de un sistema caso a caso: solo cuentan los casos en que discrepan. Un p-valor alto quiere decir que la diferencia puede ser azar. → [Métricas deterministas](../../04-evals/03-metricas-deterministas/)

**MCP**. Model Context Protocol: un protocolo abierto para exponer herramientas y datos a los modelos de forma estándar, con un servidor que cualquier cliente compatible puede usar. → [MCP](../../05-agentes/10-mcp/)

**Memoria (de un agente)**. Lo que el agente conserva entre pasos o conversaciones, y cómo se resume o recorta para que quepa en el contexto. → [Estado, memoria y contexto](../../05-agentes/07-estado-memoria-y-contexto/)

**Modelo abierto**. Modelo cuyos pesos se pueden descargar y ejecutar en tu infraestructura (*open weights*). Lo que puedes hacer con él lo dice su licencia. → [Modelos abiertos](../../07-modelos-propios/02-modelos-abiertos/)

**Multiagente**. Sistema en el que varios agentes, con papeles distintos, colaboran o se reparten una tarea. → [Sistemas multiagente desde cero](../../05-agentes/09-sistemas-multiagente-desde-cero/)

## O

**Observabilidad**. Poder saber qué pasa dentro del sistema por sus señales: trazas, métricas y registros. → [Observabilidad](../../06-produccion/02-observabilidad/)

**OpenTelemetry**. Estándar abierto para emitir trazas y métricas. Tiene convenciones propias para las llamadas a modelos (`gen_ai.*`). → [Observabilidad](../../06-produccion/02-observabilidad/)

## P

**pass@k y pass^k**. Métricas para sistemas que no responden siempre igual: si acierta al menos una de k veces (pass@k) o las k veces (pass^k). → [Evals de agentes](../../05-agentes/12-evals-de-agentes/)

**Perplejidad**. Lo "sorprendido" que está un modelo con un texto. Sirve para comparar versiones del mismo modelo, pero no mide tu tarea. → [Cuantización](../../07-modelos-propios/04-cuantizacion/)

**Plantilla de chat**. La forma de convertir la lista de mensajes en el texto con marcas especiales que el modelo vio al entrenarse. Sin ella, el modelo no sabe que le toca responder. → [Modelos abiertos](../../07-modelos-propios/02-modelos-abiertos/)

**Prefill y decode**. Las dos fases de la generación: procesar el prompt entero (prefill, de donde sale el tiempo hasta el primer token) y generar token a token (decode). → [Inferencia local (Ollama, llama.cpp, vLLM)](../../07-modelos-propios/03-inferencia-local/)

**Prompt de sistema**. Las instrucciones generales del modelo, separadas de los mensajes del usuario. → [Anatomía de un prompt](../../02-prompting/01-anatomia-de-un-prompt/)

## R

**RAG**. Generación aumentada por recuperación: buscar en tus documentos los fragmentos relevantes y dárselos al modelo junto a la pregunta. → [Cuándo usar RAG (y cuándo no)](../../03-rag/01-cuando-usar-rag/)

**Ranura (slot)**. En llama-server, cada petición que se puede atender a la vez. El contexto total se reparte entre las ranuras. → [Inferencia local (Ollama, llama.cpp, vLLM)](../../07-modelos-propios/03-inferencia-local/)

**Recall y precisión**. En la búsqueda, qué parte de lo relevante se recupera (recall) y qué parte de lo recuperado es relevante (precisión). → [Evals de RAG](../../04-evals/05-evals-de-rag/)

**Reranking**. Reordenar los candidatos de una primera búsqueda con un modelo más preciso (un cross-encoder), que lee la pregunta y cada fragmento juntos. → [Reranking](../../03-rag/05-reranking/)

**Respaldo (fallback)**. El modelo o la respuesta que se usa cuando el principal falla o tarda demasiado. Su calidad también se mide. → [Arquitectura](../../06-produccion/01-arquitectura/)

## S

**Safetensors**. Formato para guardar pesos que solo contiene tensores: abrirlo no ejecuta código, al contrario que el formato pickle de PyTorch. → [Modelos abiertos](../../07-modelos-propios/02-modelos-abiertos/)

**Salida estructurada**. Pedir al modelo una respuesta con un formato fijo (normalmente JSON con un esquema) y validarla en el código. → [Salida estructurada](../../02-prompting/03-salida-estructurada/)

**Sampling**. Cómo se elige cada token entre los posibles: la temperatura, top-p y top-k controlan cuánta variación hay. → [Sampling](../../01-fundamentos-de-llms/03-sampling/)

**SLO**. Objetivo de nivel de servicio: el valor que una métrica (latencia, errores) debe cumplir, y que decide cuándo alertar. → [Métricas operativas](../../06-produccion/03-metricas-operativas/)

**Sobreajuste (overfitting)**. Cuando un modelo aprende de memoria los ejemplos de entrenamiento: su pérdida sigue bajando mientras la de una validación que no ve se estanca o sube. → [Fine-tuning con LoRA/QLoRA](../../07-modelos-propios/05-fine-tuning-con-lora-qlora/)

**Subagente**. Agente al que otro delega una tarea con su propio contexto aislado, y del que recibe solo el resultado. → [Subagentes](../../05-agentes/08-subagentes/)

## T

**Token**. La unidad de texto con la que trabaja el modelo: un trozo de palabra, una palabra o un signo. Se cobra y se mide por tokens. → [Cómo funciona un LLM](../../01-fundamentos-de-llms/01-como-funciona-un-llm/)

**Tool calling**. Que el modelo pida ejecutar una función (con sus argumentos) en lugar de responder. El código la ejecuta y le devuelve el resultado. → [Tool calling básico](../../02-prompting/04-tool-calling-basico/)

**Traza y span**. Una traza es el recorrido de una petición por el sistema; cada paso (la búsqueda, la llamada al modelo) es un span, con su duración y sus atributos. → [Observabilidad](../../06-produccion/02-observabilidad/)

**TTFT (tiempo hasta el primer token)**. Lo que tarda en llegar el primer fragmento de la respuesta en streaming. Es la latencia que percibe el usuario. → [APIs y SDKs](../../01-fundamentos-de-llms/04-apis-y-sdks/)

## W

**Workflow**. Secuencia de pasos con LLMs en la que el código decide el orden. Más predecible y fácil de evaluar que un agente; si basta, es preferible. → [Workflow frente a agente](../../05-agentes/01-workflow-frente-a-agente/)

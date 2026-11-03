# Plan del curso

Estado: `⬜ pendiente` · `🟨 en curso` · `✅ hecho`

Cada lección sigue la estructura definida en `CLAUDE.md`. El bloque **Mide y depura** es obligatorio en todas.

---

## Módulo 0 — Introducción 🟨

1. **La rotación**: del folio en blanco al TFM *(guía general de la transición; la historia personal va en el anexo H)*
2. Qué hace un AI Engineer (y qué no): frente a ML Engineer, Data Scientist y dev "que usa IA"
3. Cómo usar este curso: estructura, prerrequisitos, ritmo, tu fork del repo
4. Entorno de trabajo: Python, uv, Ollama, claves API, `.env`, primer "hola mundo" con un LLM
5. Tu proyecto en VS Code: terminal integrada, tareas, depuración y tests

## Módulo 1 — Fundamentos de LLMs 🟨

1. Cómo funciona un LLM sin matemáticas innecesarias: tokens, predicción, contexto
2. Ventana de contexto, límites y qué pasa cuando te pasas
3. Sampling: temperature, top_p y determinismo (o su ausencia)
4. APIs y SDKs: llamada mínima, streaming, mensajes y roles
5. Modelos abiertos frente a cerrados; primer contacto con Hugging Face
6. Coste y latencia: cómo se calculan y cómo medirlos
7. Modelos que razonan: tokens de razonamiento, coste, latencia y límites
- **Práctica transversal**: nace `curso_core` con un cliente LLM que registra tokens, latencia y coste por llamada
- **Errores clave**: 401, 429 (rate limit), context length exceeded, timeouts; reintentos con backoff

## Módulo 2 — Prompting y salida estructurada 🟨

1. Anatomía de un prompt: system, instrucciones, contexto, ejemplos
2. Few-shot y técnicas que sí funcionan (y mitos que no)
3. Salida estructurada: JSON Schema y Pydantic
4. Tool calling básico
5. Prompts como código: versionado y plantillas
6. **Tu primera eval**: 10 casos, una aserción, un número
- **Errores clave**: JSON inválido, fallos de validación, truncamiento por `max_tokens`, regresiones al cambiar un prompt

## Módulo 3 — RAG 🟨

1. Cuándo usar RAG (y cuándo no)
2. Ingesta y chunking: estrategias y sus consecuencias
3. Embeddings y bases vectoriales
4. Recuperación: densa, léxica (BM25) e híbrida
5. Reranking
6. Generación con citas y control de alucinaciones
- **Métricas**: recall@k, MRR, fidelidad de la respuesta al contexto
- **Errores clave**: chunks que parten la idea, recuperación vacía, alucinación pese a buen contexto, modelo de embeddings distinto en indexación y consulta

## Módulo 4 — Evals 🟨

1. Por qué evaluar: "parece que funciona" no es una métrica
2. Datasets de referencia: cómo construirlos y mantenerlos
3. Métricas deterministas
4. LLM-as-judge: cómo montarlo y sus sesgos
5. Evals de RAG: medir cada etapa y dónde se pierde cada fallo
6. Análisis de errores: clasificar fallos e iterar con datos
7. Evals en CI: detectar regresiones
- **Decisiones**: se evalúan los sistemas ya construidos (tickets del módulo 2 y RAG del módulo 3); el núcleo de evals vive en `curso_core.evals`, sin frameworks (comparativa en el anexo F); en CI, métricas deterministas sobre respuestas grabadas en cada PR y la eval completa con modelo en un flujo manual o nocturno. Las evals de agentes van en el módulo 5. El dataset se ancla al corpus: cada pregunta lleva sus segmentos de referencia (frases literales del corpus, comprobadas por un test) y un tipo (con respuesta, sin respuesta con el tema en el corpus, fuera de ámbito, guardarraíl) con su comportamiento esperado; en las que no deben responderse, la puntuación se invierte y se mide aparte. Las etiquetas para calibrar el juez también se anclan a segmentos
- **Errores clave**: un juez que siempre aprueba (o que siempre suspende), datasets contaminados, sobreajuste al set de evaluación

## Módulo 5 — Agentes 🟨

1. Workflow frente a agente: no todo necesita autonomía
2. Diseño de herramientas: tool use a fondo
3. El bucle de un agente desde cero (sin framework)
4. Planificar: tareas, dependencias y replanificación
5. Grafos de estado desde cero: nodos, aristas condicionales, checkpoints y aprobación humana
6. LangGraph: el mismo grafo con un framework
7. Estado, memoria y contexto
8. Subagentes: delegar con contexto aislado
9. Sistemas multiagente desde cero: cuándo compensa y cuándo es complejidad gratuita
10. MCP: conectar herramientas de forma estándar
11. Seguridad de agentes: permisos, aprobación humana e inyección
12. Evals de agentes: resultado, trayectoria, fiabilidad y coste
13. Agentes que aguantan: reanudar, reintentar y presupuestos
14. Panorama: SDK de agentes, skills, A2A y lo que viene
15. Cierre: un comité de crisis multiagente, medido frente al agente único
- **Decisiones** (aprobadas el 2026-10-31, ver `docs/PROPUESTA-modulo-5.md`; ampliado a 14 lecciones el mismo día, a petición de Alex, y a 15 el 2026-11-01 con el cierre como lección propia): cierre del módulo con un sistema de guardia multiagente construido desde cero (orquestador que planifica el incidente como grafo de tareas, subagentes especializados, aprobación humana), medido frente al agente único; caso único, un agente de guardia sobre la plataforma de los módulos 2-4 (corpus, tickets, RAG), construido como workflow, como agente desde cero y como grafo; grafo propio antes que LangGraph; MCP con el SDK oficial sobre la revisión 2026-07-28; lo que caduca rápido va en la lección 9 (con nota "Revisado") y el detalle de herramientas en un anexo; el modelo local para agentes se elige midiendo en la lección 2
- **Mide y depura**: trazas de agente paso a paso; pasos por tarea, terminación (resuelta, límite, error) y coste por tarea resuelta
- **Errores clave**: bucles infinitos, argumentos de herramienta alucinados, explosión de coste, pérdida de estado, inyección a través del resultado de una herramienta
- **Estado** (2026-11-01): las 15 lecciones escritas, con salidas reales; pendiente de la revisión de Alex. LangGraph (lección 6) y el SDK de MCP (lección 10) entran como dependencias del curso. La lección 15 es el cierre que pedía la decisión (orquestador que planifica encargos como grafo, especialistas técnico, legal, de negocio y de comunicación con sus propias políticas, y aprobación humana), sobre cuatro incidentes de negocio, medido frente al agente único con el modelo local y con uno comercial (decisión de Alex, 2026-11-01). Las políticas e incidentes de la lección 15 son ficticios, salvo el plazo de 72 horas del RGPD

## Módulo 6 — Producción 🟨

1. Arquitectura: API, colas, caché, fallbacks
2. Observabilidad: trazas (OpenTelemetry, Langfuse u equivalentes)
3. Métricas operativas: latencia p50/p95, coste por petición, tasa de error, uso de tokens
4. Seguridad: prompt injection, gestión de secretos, datos personales
5. Guardrails y validación de entrada y salida
6. Despliegue: contenedores y cloud
7. Lectura de incidentes: de la alerta a la causa raíz
8. Cambios seguros: en sombra, canario y vuelta atrás
9. Calidad en producción: evaluación en línea sin respuesta correcta
- **Errores clave**: secretos en el repo y cómo limpiar el historial, degradación silenciosa, costes descontrolados
- **Decisiones** (2026-11-01, tomadas por Claude y validadas por Alex el 2026-11-03, con la 6.08 y la 6.09): el caso del módulo es el sistema vigente del módulo 4 servido como API (FastAPI), "lo que se despliega es lo que se midió"; trazas con OpenTelemetry (curso_core emite los spans con los atributos `gen_ai.*`; Jaeger opcional con Docker) y métricas en formato Prometheus, los dos estándares abiertos
- **Estado** (2026-11-03): las 9 lecciones escritas, con salidas reales; pendiente de la revisión de Alex. La 9 (petición de Alex, 2026-11-03: las cuatro métricas de RAG también en producción) juzga una muestra del tráfico con fidelidad, relevancia y precisión del contexto y las publica por versión. La 8 (decisión de Alex, 2026-11-02: profundizar en operación y recuperación de fallos) mide en sombra, canario y vuelta atrás el cambio de modelo de la 7

## Módulo 7 — Modelos propios 🟨

1. Prompting, RAG o fine-tuning: cómo decidir
2. Modelos abiertos: descargar y preparar para servir (elegir modelo en el Hub está en el anexo B.1)
3. Inferencia local (Ollama, llama.cpp, vLLM)
4. Cuantización
5. Fine-tuning con LoRA/QLoRA
6. Evaluar el modelo ajustado frente al base
- **Errores clave**: falta de memoria en GPU, plantilla de chat incorrecta, sobreajuste, mejoras que no lo son
- **Decisiones** (2026-11-02, tomadas por Claude y validadas por Alex el 2026-11-03, también el cierre con resultado negativo): el caso sigue siendo el asistente. La 7.01 mide que los fallos del modelo de 1,5B con RAG frente al de 7B son de comportamiento, así que la hipótesis de las lecciones 5 y 6 es ajustar el de 1,5B con LoRA usando las respuestas del de 7B (destilación) y medirlo con la eval del módulo 4. La idea de desplegar modelos propios como en empresa queda repartida entre el módulo 6 (servir) y este (descargar, cuantizar, ajustar)
- **Estado** (2026-11-02): las 6 lecciones escritas, con salidas reales; pendiente de la revisión de Alex. Resultado de la 7.06, con dos iteraciones (la segunda con los datos corregidos) y servido en vLLM y en GGUF con llama.cpp: el ajuste con LoRA no compensa con estos datos (41-42 de 58, sin diferencia significativa con el base; el maestro, 52), aunque es 14 veces más rápido que el 7B

## Módulo 8 — Proyecto final 🟨

1. Especificación: el alumno elige dominio y problema
2. Requisitos mínimos: proyecto propio creado desde cero, desarrollo, evals, observabilidad, documentación y análisis de coste
3. Rúbrica de evaluación
4. Cómo presentarlo como proyecto de portafolio
- **Decisiones** (Alex, 2026-11-02): práctica con plantilla de proyecto y comprobador de requisitos (`proyecto.toml` + `comprobar_proyecto.py`); rúbrica por niveles (insuficiente, suficiente, sólido) sin nota, contrastada con la evidencia (`rubrica.py`); explicar decisiones en entrevistas va en la lección 4. El ejemplo resuelto es el asistente del curso
- **Estado** (2026-11-02): las 4 lecciones escritas, con salidas reales; pendiente de la revisión de Alex

---

## Anexos 🟨

- **A. La API de Claude**: el proveedor anthropic de curso_core, sus diferencias con el formato de OpenAI, modelos y coste
  - **Decisiones** (Alex, 2026-11-03): sin secciones personales; Claude Code va en el anexo C
- **B. Hugging Face**: el ecosistema más usado en empresa, como laboratorio: elegir modelo, arquitecturas, clasificación, datasets e infraestructura del Hub
  - **B.1 El Hub y elegir modelo**: fichas, licencias, datos de entrenamiento, búsqueda con `huggingface_hub`
  - **B.2 Encoder, decoder y encoder-decoder**: qué hace cada uno y cuándo usarlo
  - **B.3 Laboratorio: clasificador de sentimiento**: encoders del Hub, LLM sin ejemplos y embeddings con regresión, medidos
  - **B.4 Datasets**: cargar, transformar, streaming y subir uno propio, privado y versionado
  - **B.5 El Hub como infraestructura**: Inference Providers, buckets, Spaces, Inference Endpoints y planes de empresa
  - **Decisiones** (Alex, 2026-11-01): varias páginas; dependencias en un grupo opcional (`uv sync --group hf`, torch para CPU); repos de ejemplo privados en la cuenta de Alex; elegir modelo vive aquí y la lección 7.2 lo enlaza
- **C. Herramientas y estrategias de desarrollo con IA**: agentes de código, graph prompting, flujos de trabajo y repos útiles
  - **Decisiones** (Alex, 2026-11-02): «graph prompting» es Graph of Thoughts; lo escribe Claude sin contenido personal (2026-11-03: sin hueco personal)
- **D. Glosario**
  - Generado con una comprobación de que cada lección enlazada contiene el término
- **E. Recursos**: papers, blogs y cursos que merecen la pena
- **F. Herramientas de evals**: Ragas, DeepEval, promptfoo e Inspect frente a lo construido en el módulo 4
- **G. APIs comerciales**: usar OpenAI, Claude u otro proveedor en lugar del modelo local, como opción, con su coste medido
  - **Decisiones** (Alex, 2026-11-02): cada lección con modelos tiene un recuadro «Con una API» con el comando (`CURSO_PROVEEDOR=openai|hf|claude`) en bash y PowerShell y el estado de sus prácticas, probado con `compatibilidad.py` (tres llamadas por práctica y proveedor). Las salidas de las lecciones siguen siendo las locales. Claude, sin probar hasta que Alex añada su clave
- **H. El proceso del autor**: por qué Alex pasó a AI Engineering y por qué existe el curso. Opcional y aparte del aprendizaje
  - **Decisiones** (Alex, 2026-11-03): un solo texto personal, no uno por módulo; escrito por Alex en `bitacora/proceso.md`, con el estilo corregido
- **I. Preguntas de entrevista**: las preguntas que más se repiten en entrevistas de AI Engineer, qué buscan y cómo responderlas con lo medido en el curso
  - **Decisiones** (Alex, 2026-11-02): anexo propio, enlazado desde la 8.04; respuestas escritas para el curso a partir de guías públicas, con enlace a la lección que tiene el dato
- **Estado** (2026-11-02): todos escritos (el H, por Alex, 2026-11-03)
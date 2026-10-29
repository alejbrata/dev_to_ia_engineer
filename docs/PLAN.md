# Plan del curso

Estado: `⬜ pendiente` · `🟨 en curso` · `✅ hecho`

Cada lección sigue la estructura definida en `CLAUDE.md`. El bloque **Mide y depura** es obligatorio en todas.

---

## Módulo 0 — Introducción 🟨

1. **La rotación**: del folio en blanco al TFM *(guía general de la transición + historia personal de `bitacora/00-introduccion.md`)*
2. Qué hace un AI Engineer (y qué no): frente a ML Engineer, Data Scientist y dev "que usa IA"
3. Cómo usar este curso: estructura, prerrequisitos, ritmo
4. Entorno de trabajo: Python, uv, VS Code, claves API, `.env`, primer "hola mundo" con un LLM

## Módulo 1 — Fundamentos de LLMs 🟨

1. Cómo funciona un LLM sin matemáticas innecesarias: tokens, predicción, contexto
2. Ventana de contexto, límites y qué pasa cuando te pasas
3. Sampling: temperature, top_p y determinismo (o su ausencia)
4. APIs y SDKs: llamada mínima, streaming, mensajes y roles
5. Modelos abiertos frente a cerrados; primer contacto con Hugging Face
6. Coste y latencia: cómo se calculan y cómo medirlos
- **Práctica transversal**: nace `curso_core` con un cliente LLM que registra tokens, latencia y coste por llamada
- **Errores clave**: 401, 429 (rate limit), context length exceeded, timeouts; reintentos con backoff

## Módulo 2 — Prompting y salida estructurada ⬜

1. Anatomía de un prompt: system, instrucciones, contexto, ejemplos
2. Few-shot y técnicas que sí funcionan (y mitos que no)
3. Salida estructurada: JSON Schema y Pydantic
4. Tool calling básico
5. Prompts como código: versionado y plantillas
6. **Tu primera eval**: 10 casos, una aserción, un número
- **Errores clave**: JSON inválido, fallos de validación, truncamiento por `max_tokens`, regresiones al cambiar un prompt

## Módulo 3 — RAG ⬜

1. Cuándo usar RAG (y cuándo no)
2. Ingesta y chunking: estrategias y sus consecuencias
3. Embeddings y bases vectoriales
4. Recuperación: densa, léxica (BM25) e híbrida
5. Reranking
6. Generación con citas y control de alucinaciones
- **Métricas**: recall@k, MRR, fidelidad de la respuesta al contexto
- **Errores clave**: chunks que parten la idea, recuperación vacía, alucinación pese a buen contexto, modelo de embeddings distinto en indexación y consulta

## Módulo 4 — Evals ⬜

1. Por qué evaluar: "parece que funciona" no es una métrica
2. Datasets de referencia: cómo construirlos y mantenerlos
3. Métricas deterministas
4. LLM-as-judge: cómo montarlo y sus sesgos
5. Evals de RAG y de agentes
6. Análisis de errores: clasificar fallos e iterar con datos
7. Evals en CI: detectar regresiones
- **Errores clave**: un juez que siempre aprueba, datasets contaminados, sobreajuste al set de evaluación

## Módulo 5 — Agentes ⬜

1. Workflow frente a agente: no todo necesita autonomía
2. Tool use a fondo
3. El bucle de un agente desde cero (sin framework)
4. Frameworks (p. ej. LangGraph): qué te dan cuando ya entiendes el bucle
5. Estado y memoria
6. Multiagente: cuándo compensa y cuándo es complejidad gratuita
7. MCP: conectar herramientas de forma estándar
- **Mide y depura**: trazas de agente paso a paso
- **Errores clave**: bucles infinitos, argumentos de herramienta alucinados, explosión de coste, pérdida de estado

## Módulo 6 — Producción ⬜

1. Arquitectura: API, colas, caché, fallbacks
2. Observabilidad: trazas (OpenTelemetry, Langfuse u equivalentes)
3. Métricas operativas: latencia p50/p95, coste por petición, tasa de error, uso de tokens
4. Seguridad: prompt injection, gestión de secretos, datos personales
5. Guardrails y validación de entrada y salida
6. Despliegue: contenedores y cloud
7. Lectura de incidentes: de la alerta a la causa raíz
- **Errores clave**: secretos en el repo y cómo limpiar el historial, degradación silenciosa, costes descontrolados

## Módulo 7 — Modelos propios ⬜

1. Prompting, RAG o fine-tuning: cómo decidir
2. Modelos abiertos en Hugging Face: elegir, descargar, licencias
3. Inferencia local (Ollama, llama.cpp, vLLM)
4. Cuantización
5. Fine-tuning con LoRA/QLoRA
6. Evaluar el modelo ajustado frente al base
- **Errores clave**: falta de memoria en GPU, plantilla de chat incorrecta, sobreajuste, mejoras que no lo son

## Módulo 8 — Proyecto final ⬜

1. Especificación: el alumno elige dominio y problema
2. Requisitos mínimos: desarrollo, evals, observabilidad, documentación y análisis de coste
3. Rúbrica de evaluación
4. Cómo presentarlo como proyecto de portafolio

---

## Anexos ⬜

- **A. Claude y Claude Code**: consejos prácticos desde el uso real (sin copiar documentación oficial)
- **B. Hugging Face**: Hub, transformers, datasets y Spaces
- **C. Herramientas y estrategias de desarrollo con IA**: agentes de código, graph prompting, flujos de trabajo y repos útiles
- **D. Glosario**
- **E. Recursos**: papers, blogs y cursos que merecen la pena
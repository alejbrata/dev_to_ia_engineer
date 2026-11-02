---
title: "E. Recursos"
description: "Recursos: los papers, blogs, libros y cursos que merecen la pena, seleccionados entre los que cita el curso y ordenados por para qué sirven"
---

:::note[Revisado: 2026-11]
Una selección corta, no una lista exhaustiva: casi todo sale de las secciones "Para profundizar" de las lecciones, donde tienes las fuentes de cada tema. Los blogs y los cursos cambian; los papers, no.
:::

## Para orientarte

- [The Rise of the AI Engineer](https://www.latent.space/p/ai-engineer), de Latent Space: el texto que puso nombre al puesto y lo separa del de ML Engineer. Lección 0.02.
- [AI Engineering](https://huyenchip.com/books/), de Chip Huyen: el libro más completo sobre construir aplicaciones con modelos fundacionales, de la evaluación al despliegue.
- [What We Learned from a Year of Building with LLMs](https://applied-llms.org/): lecciones de equipos que han llevado sistemas con LLMs a producción, de lo táctico a lo estratégico.
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), de Anthropic: cuándo un workflow basta y cuándo compensa un agente. Módulo 5.

## Sobre evaluación

Es lo que más distingue a un AI Engineer, y donde más se aprende leyendo a quien lo hace a diario:

- [Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/), de Hamel Husain: por qué la eval va primero y cómo empezar.
- [Task-Specific LLM Evals that Do & Don't Work](https://eugeneyan.com/writing/evals/), de Eugene Yan: qué métricas funcionan para cada tarea.
- [Who Validates the Validators?](https://arxiv.org/abs/2404.12272): cómo alinear un juez LLM con el criterio humano. Lección 4.04.
- [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685): los sesgos de los jueces LLM, medidos.
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), de Anthropic: evaluar agentes, por resultado y por trayectoria. Lección 5.12.

## Papers que conviene haber leído

Uno por tema, de los que sostienen lo que hace el curso:

| Tema | Paper | Lección |
| --- | --- | --- |
| Transformers | [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | B.2 |
| Few-shot | [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) | 2.02 |
| Razonamiento | [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) | 1.07 |
| Contexto largo | [Lost in the Middle](https://arxiv.org/abs/2307.03172) | 1.02 |
| RAG | [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) | 3.01 |
| Búsqueda | [BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663) | 3.04 |
| Evals de RAG | [Ragas: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217) | 4.05 |
| Agentes | [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) | 5.01 |
| Herramientas | [Toolformer](https://arxiv.org/abs/2302.04761) | 2.04 |
| Seguridad | [Not what you've signed up for: inyección indirecta](https://arxiv.org/abs/2302.12173) | 6.04 |
| Servir modelos | [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180) | 7.03 |
| Ajuste fino | [LoRA](https://arxiv.org/abs/2106.09685) y [QLoRA](https://arxiv.org/abs/2305.14314) | 7.05 |
| Ajustar o recuperar | [Fine-Tuning or Retrieval? Comparing Knowledge Injection in LLMs](https://arxiv.org/abs/2312.05934) | 7.01 |

## Producción

Casi nada de esto es específico de los LLMs, y por eso a quien viene de backend le resultará familiar:

- [Site Reliability Engineering](https://sre.google/sre-book/table-of-contents/), de Google: SLO, incidentes, postmortems y sobrecarga. Módulo 6.
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/): los riesgos de seguridad propios de las aplicaciones con LLMs. Lecciones 5.11 y 6.04.
- [The lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/), de Simon Willison: la combinación de datos privados, contenido no confiable y salida al exterior que hace explotable a un agente.
- [Convenciones semánticas de OpenTelemetry para IA generativa](https://github.com/open-telemetry/semantic-conventions-genai): los atributos estándar de las trazas de llamadas a modelos. Lección 6.02.
- [Timeouts, retries and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/), de la Builders' Library de AWS: reintentos que no tumban al proveedor. Lecciones 1.06 y 5.13.

## Cursos

- [LLM Course de Hugging Face](https://huggingface.co/learn/llm-course/chapter1/1): transformers, tokenizadores, ajuste fino y el ecosistema del Hub, con código. Complementa el anexo B y el módulo 7.
- [Cursos cortos de DeepLearning.AI](https://www.deeplearning.ai/short-courses/): cursos de una o dos horas sobre temas concretos (RAG, agentes, evaluación), muchos hechos con las empresas que crean las herramientas. Útiles para conocer una herramienta; el criterio de cuándo usarla sigue siendo tuyo.

## Para seguir la actualidad

El campo cambia cada mes. Pocas fuentes, bien elegidas, bastan:

- [Simon Willison's Weblog](https://simonwillison.net/): pruebas prácticas de casi cada modelo y herramienta nuevos, con sus problemas de seguridad.
- [Latent Space](https://www.latent.space/): la publicación (y el podcast) de referencia sobre AI Engineering.
- [Blog de ingeniería de Anthropic](https://www.anthropic.com/engineering) y [blog de Hugging Face](https://huggingface.co/blog): cómo construyen sus sistemas los que hacen los modelos.
- Clasificaciones para elegir modelo según la tarea: [MTEB](https://huggingface.co/spaces/mteb/leaderboard) para embeddings (lección 3.03) y la de [Berkeley](https://gorilla.cs.berkeley.edu/leaderboard.html) para el uso de herramientas (lección 5.02). Úsalas para preseleccionar candidatos, no para decidir: decide tu eval.

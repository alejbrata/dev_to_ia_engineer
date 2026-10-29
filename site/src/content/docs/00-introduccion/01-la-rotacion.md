---
title: "La rotación"
description: "La rotación: del folio en blanco al TFM"
---

Esta lección tiene dos capas. La primera es una guía para cualquiera que pase de backend a AI Engineering: qué traes, qué te falta y cómo organizarlo. La segunda es la historia de cómo hizo ese cambio el autor del curso, que encontrarás en la sección [Bitácora](#bitácora).

## Objetivos

Al terminar esta lección podrás:

- Identificar qué habilidades de backend se transfieren tal cual a AI Engineering.
- Enumerar lo que es nuevo y lo que conviene desaprender.
- Hacer tu autodiagnóstico y obtener un plan ordenado según el curso.
- Definir cómo vas a medir tu progreso sin contar horas de vídeo.

## Teoría

### Lo que ya traes

Si llevas años en backend, tienes más de la mitad del trabajo hecho. Un sistema basado en LLMs es, sobre todo, un sistema distribuido con una dependencia externa poco predecible. Casi todo lo que sabes sigue valiendo:

| Lo que sabes de backend | Dónde lo usarás |
| --- | --- |
| Integrar APIs de terceros, con timeouts y reintentos | Cada llamada a un modelo |
| Validar entradas y salidas | Salida estructurada, guardrails |
| Tests automatizados | La base de las evals |
| Bases de datos e índices | Bases vectoriales y búsqueda en RAG |
| Logging, métricas, APM | Trazas de llamadas y agentes |
| Colas, caché, fallbacks | Arquitectura de producción |
| Gestión de secretos y seguridad | Claves de API, prompt injection, datos personales |
| Despliegue y operación | Exactamente lo mismo |

No es poco. Mucha gente que llega a la IA desde otros perfiles tiene que aprender todo esto por el camino.

### Lo que es nuevo

Lo nuevo se concentra en entender cómo se comporta el modelo y cómo medirlo:

- **Cómo funciona un LLM** lo justo para predecir sus límites: tokens, contexto, sampling.
- **Cómo darle instrucciones y contexto**: prompting, salida estructurada, RAG.
- **Cómo darle herramientas**: tool calling y agentes.
- **Cómo medir la calidad** de algo que no siempre responde igual: evals.

### Lo que conviene desaprender

Esta parte cuesta más que la anterior, porque son reflejos que en backend funcionan bien:

- **Esperar determinismo.** La misma entrada puede dar salidas distintas. Un test que pasa una vez no demuestra nada.
- **Confiar en la especificación.** Un modelo no sigue un contrato como una API. Sigue instrucciones casi siempre, y "casi siempre" hay que medirlo.
- **Dar por terminado lo que funciona.** En backend, si los tests pasan, el trabajo suele estar hecho. Aquí, "funciona con los ejemplos que probé" es el punto de partida, no el final.

### Cómo organizar la rotación

Una transición así compite con un trabajo a tiempo completo. Lo que suele funcionar es aprender construyendo: cada tema termina en algo que se ejecuta y que puedes enseñar. Por eso cada lección de este curso acaba en código y el curso termina en un proyecto de portafolio.

## Práctica

Haz tu autodiagnóstico. Abre [`modulos/00-introduccion/autodiagnostico.toml`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/autodiagnostico.toml) y puntúa cada habilidad de 0 a 3:

| Nivel | Significado |
| --- | --- |
| 0 | Nunca lo he hecho |
| 1 | Lo he visto o lo he hecho siguiendo un tutorial |
| 2 | Lo hago, pero con ayuda o consultando a menudo |
| 3 | Lo hago solo y sabría explicarlo |

Sé honesto: nadie más lo va a ver, y un diagnóstico inflado solo te hace saltarte lo que necesitas. Luego ejecútalo:

```sh
uv run python modulos/00-introduccion/autodiagnostico.py
```

Esta es la salida para un perfil backend típico (valores de ejemplo):

```text
Fortalezas (7):
  + Programar en Python con soltura
  + Consumir APIs HTTP y manejar sus errores
  + Logs, métricas y trazas
  + Tests automatizados
  + Bases de datos y búsqueda
  + Colas, caché, reintentos y fallbacks
  + Contenedores y despliegue en cloud

Por trabajar (8), en el orden del curso:
  - Tokens, contexto y sampling (módulo 1)
  - Diseñar prompts (módulo 2)
  - Salida estructurada y tool calling (módulo 2)
  - RAG: chunking, embeddings, recuperación (módulo 3)
  - Evaluar sistemas con LLMs (módulo 4)
  - Agentes y uso de herramientas (módulo 5)
  - Secretos, validación de entradas, datos personales (módulo 6)
  - Modelos abiertos, inferencia local y fine-tuning (módulo 7)

De backend traes 7 de 8 habilidades que el curso da por útiles.
```

Si Python sale por debajo de 2, el script te lo marca aparte: es el único prerrequisito, y conviene resolverlo antes del módulo 1.

Lee el código. Usa Pydantic para validar el fichero, la misma herramienta con la que validarás las salidas de los modelos a partir del módulo 2.

## Mide y depura

El autodiagnóstico es tu línea base. Repítelo al terminar cada módulo. Si trabajas en un fork del repo y haces commit del `.toml` cada vez, tu historial de git es tu registro de progreso:

```sh
git log -p -- modulos/00-introduccion/autodiagnostico.toml
```

Pero una autoevaluación es una opinión. Mide también resultados que no dependan de cómo te sientas:

- **Prácticas ejecutadas.** No leídas: ejecutadas y modificadas.
- **Errores resueltos.** Lleva una lista de los errores que te bloquearon y cómo los resolviste. Es tu propia colección de "Anatomías de un error", y te servirá en las entrevistas.
- **Algo publicado.** Un repo, una demo, el proyecto final. Lo que otros pueden ver vale más que lo que tú sabes que sabes.

Las horas de vídeo vistas y los cursos empezados no son una métrica de progreso.

## Errores frecuentes

**Encadenar tutoriales sin construir nada.** Da sensación de avance y deja pocas habilidades. Si llevas una semana sin escribir código, para de leer.

**Perseguir cada novedad.** Cada semana sale un modelo, un framework o una técnica. Lo que no cambia es lo de este curso: medir, depurar, dar contexto, controlar coste y latencia. Aprende eso primero y las novedades se vuelven fáciles de evaluar.

**Empezar por el fine-tuning.** Parece lo más serio, pero casi siempre es lo último que necesitas. Antes van el prompting, el RAG y las evals; sin evals, ni siquiera sabrás si el ajuste mejoró algo.

**Subestimar lo que traes.** Saber operar sistemas en producción es exactamente lo que falta en muchos proyectos de IA. No lo escondas en tu CV: es tu ventaja.

### Anatomía de un error: el fichero que no valida

Rellenas el autodiagnóstico deprisa, pones un 4 en Python y escribes mal una clave (`segurida` en lugar de `seguridad`). Al ejecutar el script:

```text
Revisa autodiagnostico.toml:
3 validation errors for Autodiagnostico
backend.python
  Input should be less than or equal to 3 [type=less_than_equal, input_value=4, input_type=int]
    For further information visit https://errors.pydantic.dev/2.14/v/less_than_equal
backend.seguridad
  Field required [type=missing, input_value={'python': 4, 'apis_http'...da': 1, 'despliegue': 2}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.14/v/missing
backend.segurida
  Extra inputs are not permitted [type=extra_forbidden, input_value=1, input_type=int]
    For further information visit https://errors.pydantic.dev/2.14/v/extra_forbidden
```

**Cómo leerlo.** Pydantic no se detiene en el primer error: los lista todos. Cada bloque empieza con la ruta del campo (`backend.python`), sigue con qué falla y, entre corchetes, el tipo de error y el valor recibido. El enlace del final explica cada tipo.

**Causa.** Son dos fallos, pero producen tres errores. El 4 está fuera del rango 0-3 (`less_than_equal`). La errata genera dos: falta el campo `seguridad` (`missing`) y sobra uno que no existe, `segurida` (`extra_forbidden`).

**Solución.** Corrige el valor y el nombre de la clave. El patrón general: cuando veas un `missing` y un `extra_forbidden` con nombres parecidos, casi siempre es una errata. Vas a leer muchos errores de Pydantic en este curso, porque es lo que valida las respuestas de los modelos.

## Bitácora

TODO(alex)

## Para profundizar

- [Documentación de Pydantic](https://docs.pydantic.dev/latest/), en especial la página de [errores de validación](https://docs.pydantic.dev/latest/errors/validation_errors/).
- swyx, [The Rise of the AI Engineer](https://www.latent.space/p/ai-engineer) (2023). Sobre el perfil al que apunta esta rotación.

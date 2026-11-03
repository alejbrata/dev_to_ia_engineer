# Asistente interno de documentación técnica

Responde a las preguntas del equipo técnico de una plataforma de comercio electrónico con su
propia documentación (runbooks, postmortems, arquitectura), citando la fuente, y dice "No
aparece en la documentación" cuando no está. Es el sistema que se construye a lo largo de los
módulos 3, 4 y 6 del curso, descrito como proyecto final de ejemplo.

## Problema

Cuando hay una incidencia, el ingeniero de guardia tiene que encontrar el procedimiento
correcto entre decenas de documentos, con prisa. Un modelo de lenguaje sin documentación no
sirve: responde lo que "suele pasar", no lo que pasa en esta plataforma.

- **Usuarios:** ingenieros del equipo técnico, sobre todo los de guardia.
- **Métrica:** aciertos en las 58 preguntas del dataset del módulo 4, ancladas a fragmentos
  del corpus: con respuesta, sin respuesta, fuera de ámbito e intentos de manipulación.
- **Umbral:** 80 %.
- **Línea base:** sin documentación, el modelo de 7B acierta 2 de las 42 preguntas con
  respuesta (lección 7.01).
- **Fuera de alcance:** actuar sobre la plataforma (es el agente del módulo 5), datos
  personales y preguntas que no tratan de la plataforma.

## Cómo ejecutarlo

Desde un clon del repositorio, con [uv](https://docs.astral.sh/uv/) y
[Ollama](https://ollama.com) instalados:

```sh
uv sync
# Los modelos de los roles chat_grande, chat y embeddings de config/models.toml:
ollama pull <modelo>
# El reranker, con llama-server: el comando está en el rol reranker de config/models.toml.

# La eval (unos 15 minutos en CPU) y el control de regresiones contra la rama principal:
uv run python modulos/04-evals/evaluar.py
uv run python modulos/04-evals/regresion.py --contra origin/main

# El servicio:
uv run uvicorn servicio:app --app-dir modulos/06-produccion --port 8100
# o en contenedores: modulos/06-produccion/compose.yaml (lección 6.06)
```

## Resultados

| Sistema | Aciertos (58) | IC 95 % | Lección |
| --- | --- | --- | --- |
| 7B sin documentación (línea base) | 16 | | 7.01 |
| 1,5B con el mismo RAG | 40 | 56 %-79 % | 6.01 |
| **7B con RAG, reranker y prompt con reglas (vigente)** | **52** | **79 %-95 %** | 4.07 |
| El mismo sistema con un modelo comercial | 53 | 81 %-96 % | anexo G |

- El sistema vigente acierta 52 de 58 (90 %). El intervalo del 95 % baja hasta el 79 %: con
  58 casos no se puede asegurar que supere el umbral del 80 %, aunque es lo más probable.
- El modelo comercial acierta uno más; caso a caso, la diferencia no es significativa
  (p = 1,00).

Cada cifra se reproduce con el comando de su lección; la del sistema vigente, con
`uv run python modulos/04-evals/evaluar.py`.

## Decisiones

- **RAG y no ajuste fino.** Sin documentación, los modelos aciertan 1 o 2 de 42 preguntas
  con respuesta: el problema es de conocimiento, y el conocimiento cambia con cada documento.
  Lección 7.01.
- **Reranker sobre la búsqueda densa.** Con k = 3, acierta 33 de las 42 preguntas con
  respuesta frente a 28 (7 casos ganados y 2 perdidos, p = 0,18). Con 42 preguntas no basta
  para afirmar que mejora, y se dice así. Lección 4.05.
- **Prompt con reglas, salido del análisis de errores.** En desarrollo, de 30 a 36 de 39
  (p = 0,03); en prueba, de 13 a 16 de 19 (p = 0,38), una mejora que encoge al pasar a
  prueba. Lección 4.06.
- **Modelo de 7B y no el de 1,5B.** 52 frente a 40 aciertos, a cambio de unos 11,5 s por
  respuesta frente a 2,6 s en CPU. El de 1,5B queda como respaldo. Lecciones 6.01 y 7.01.
- **Caché con la huella del sistema y el modelo en la clave.** Con preguntas repetidas, la
  mediana baja de 13,4 s a 3 ms; la huella invalida la caché cuando cambia el sistema
  (lección 6.01), y el modelo, cuando cambia por configuración: con solo la huella, tras
  volver atrás un canario, 12 de 27 respuestas seguían siendo del modelo nuevo (lección 6.08).
- **Cambios de modelo en sombra antes del canario.** El de 1,5B como principal perdía 12
  casos en sombra (p = 0,000) y en canario parecía mejor en todas las señales. Lección 6.08.
- **Calidad en producción con jueces sobre una muestra.** Fidelidad, relevancia y precisión
  del contexto por versión en `/metrics` (`ASISTENTE_CALIDAD`). Con las 58 preguntas, la
  regla de vuelta atrás salta por fidelidad (79 % frente a 95 %). Lección 6.09.
- **Valoraciones de los usuarios, revisadas antes de entrar en la eval.** Cada respuesta lleva
  un id para valorarla (`POST /valoraciones`). En el canario simulado, 9 de los 15 grupos de 👎
  eran falsas alarmas; los 3 fallos nuevos confirmados entraron en el dataset. Lección 6.10.
- **Guardrails de entrada y salida.** De nueve ataques, seis funcionan sin guardrails y uno
  con ellos, sin estropear ninguna de las 58 respuestas normales. Lección 6.05.

## Coste

- Unos 620 tokens de entrada (pregunta, reglas y tres fragmentos) y 38 de salida por
  pregunta que llega al modelo. Lección 6.03.
- Con el modelo local, el coste es la máquina: en CPU, unos 11,5 s por respuesta.
- Con un modelo comercial barato como referencia, 0,025 $ por cada mil preguntas con el
  tráfico normal (el 70 % lo sirve la caché) y 0,081 $ en un pico sin caché. Lección 6.03.
- No hay una proyección con un volumen real: el proyecto no tiene usuarios reales.

## Límites

- **El intervalo de la eval** baja del umbral (ver Resultados). Más casos lo estrecharían.
- **El corpus y el dataset son del curso:** documentación inventada de una plataforma de
  ejemplo, no de una empresa real.
- **La latencia en CPU** (unos 11,5 s) es alta para una guardia. Con GPU, o con el modelo de
  1,5B si se acercara al de 7B, bajaría (módulo 7).
- **Con carga, el respaldo responde peor:** 40 de 58 frente a 52, y en un pico atiende la
  mitad de las preguntas sin que salte ningún error. Lecciones 6.01 y 6.03.
- **Documentos envenenados:** una página del runbook editada con instrucciones llega al
  prompt en 3 de 7 preguntas, y el asistente obedece en una. Los guardrails no paran la
  edición que no tiene una forma reconocible. Lecciones 6.04 y 6.05.
- **La huella no ve el cambio de modelo por entorno** (`CURSO_ROLES`); `/salud` muestra el
  modelo que sirve cada rol para detectarlo. Lección 6.07.
- **La calidad en línea es cara y lenta de decidir:** juzgar una respuesta tarda unas tres
  veces lo que generarla, y ver una caída de fidelidad como la del 1,5B pide unas 63
  evaluaciones por versión (630 respuestas del canario con un muestreo del 10 %). El juez de
  relevancia falla más con las respuestas de una palabra del 7B. Lección 6.09.

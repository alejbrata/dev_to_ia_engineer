---
title: "Evals en CI"
description: "Llevar las evals a la integración continua: un control sin modelo en cada PR sobre respuestas grabadas, con huella para detectar resultados desactualizados, y la eval completa con modelos aparte"
---

:::note[Revisado: 2026-10]
Las salidas son reales. El sistema vigente es el elegido en la lección 06: reranker, 3 fragmentos, el prompt `rag/con-citas-reglas` y Qwen2.5 7B Instruct (rol `chat_grande`), en Ollama, sobre CPU. El CI usa GitHub Actions.
:::

## Objetivos

Al terminar esta lección podrás:

- Separar las evals en dos niveles: un control rápido y sin modelo en cada PR, y la eval completa con modelos, a mano o cada noche.
- Detectar en CI que los resultados grabados ya no corresponden al código (huella de los ficheros).
- Definir cuándo un cambio es una regresión: el total y los casos críticos.
- Leer el fallo de un control de regresiones y saber qué hacer en cada caso.

## Teoría

### El problema: una eval con modelos no cabe en cada PR

En la lección 06 del módulo 2 viste que una eval que termina con código de error puede bloquear un cambio, como un test que falla. Llevarla a CI tiene un problema práctico: la eval completa de este módulo tarda unos 12 minutos con el modelo de 7B en la máquina del curso, necesita Ollama, el reranker y varios GB de modelos, y no es del todo determinista. Ejecutarla en cada PR, en un runner de GitHub sin GPU, sería lento y caro, y daría falsos fallos por ruido.

La solución habitual es separarla en dos niveles, como se decidió al planificar el módulo:

1. **En cada PR, sin modelo.** Las respuestas del sistema están grabadas en el repositorio (`resultados/vigente.jsonl`). El CI no las genera: comprueba que están al día, las vuelve a puntuar con los comprobadores actuales y las compara con las de la rama base. Tarda segundos y es determinista.
2. **La eval completa, aparte.** La ejecuta quien cambia el sistema, antes de abrir el PR, o un flujo nocturno en una máquina con los modelos. Su resultado es el fichero que se graba y se revisa en el PR.

Es lo mismo que separar los tests unitarios de los de integración contra servicios reales. Los primeros corren siempre; los segundos, cuando hay entorno para ellos.

### El riesgo: resultados que ya no corresponden al código

Si las respuestas están grabadas, alguien puede cambiar el prompt, olvidarse de repetir la eval y dejar en el repositorio unas respuestas que ya no son las del sistema. El CI seguiría en verde con datos falsos.

Para evitarlo, `evaluar.py` guarda con los resultados una **huella**: un hash de los ficheros de los que dependen las respuestas (el prompt, `config/models.toml`, el código de recuperación y generación, el corpus y la propia configuración del sistema). El control recalcula la huella y, si no coincide, falla. Es la misma idea que un fichero de bloqueo de dependencias: si cambias `pyproject.toml` y no regeneras `uv.lock`, el CI te avisa.

El dataset no está en la huella a propósito. Si cambias el dato clave de una pregunta, no hace falta volver a generar las respuestas: basta con volver a puntuarlas, y eso lo hace el control. Si añades una pregunta o cambias su texto, el control lo detecta aparte, porque cada resultado guarda la pregunta que se respondió.

### Qué es una regresión

Con 58 preguntas, una diferencia de uno o dos casos puede ser ruido (lección 03). No se puede exigir significación estadística para bloquear un PR, porque casi nunca la habrá. Hace falta una regla explícita, decidida antes de ver los resultados. Aquí:

- **Menos aciertos que la rama base: falla.** Un cambio no puede empeorar el total.
- **Perder un caso crítico: falla**, aunque el total mejore. Los guardarraíles son críticos: un sistema que acierta más pero vuelve a filtrar su prompt no es mejor.
- **Casos ganados y perdidos, y la p de McNemar: se informan**, para que quien revisa el PR vea qué cambia, pero no deciden.

Las dos versiones se puntúan con los comprobadores actuales. Así, un cambio en un comprobador no aparece como una regresión del sistema.

## Práctica

El control que corre en cada PR:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/regresion.py --contra main
```

La eval completa, cuando cambias el sistema (necesita el reranker de la lección 05 del módulo 3 en marcha):

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/evaluar.py
```

[`evaluar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/evaluar.py) define el sistema vigente en una constante (`SISTEMA`), responde las 58 preguntas y guarda los resultados con la huella:

```text
52 de 58 · huella 7097dd989233952d · vigente.jsonl
```

Son las mismas 58 respuestas, una a una, que dio reglas-7b en la lección 06 (36 en desarrollo y 16 en prueba).

[`regresion.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/regresion.py) no llama a ningún modelo. Con los resultados al día:

```text
1. ¿Están al día los resultados grabados?
   huella guardada 7097dd989233952d · huella actual 7097dd989233952d

2. Respuestas grabadas, repuntuadas con los comprobadores actuales
   52 de 58

OK
```

En CI es un paso más del flujo de Python ([`python.yml`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/.github/workflows/python.yml)), después de los tests. Compara con la rama de destino en un PR y con el commit anterior en un push a `main`. Necesita el historial de git (`fetch-depth: 0`) para leer los resultados de la referencia:

```yaml
- name: Evals sin modelo (módulo 4, lección 07)
  env:
    REF: ${{ github.event_name == 'pull_request' && format('origin/{0}', github.base_ref) || github.event.before }}
  run: uv run python modulos/04-evals/regresion.py --contra "$REF"
```

La referencia se pasa por una variable de entorno, no interpolada dentro del comando. Es una buena costumbre en GitHub Actions: un valor interpolado en `run` se ejecuta como parte del script.

La eval completa tiene su propio flujo, [`evals-completas.yml`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/.github/workflows/evals-completas.yml), que se lanza a mano (y cada noche si descomentas el `schedule`). Necesita un runner propio (*self-hosted*) con Ollama, los modelos y el reranker. Con un proveedor remoto, bastaría un runner de GitHub y la clave en los secretos del repositorio. Ese flujo no se ha ejecutado en el curso, porque requiere registrar un runner; el paso de `python.yml` sí corre en cada push.

## Mide y depura

### Cambiar el prompt sin repetir la eval

Un PR cambia una frase del prompt vigente ("en dos o tres frases" pasa a "en una o dos frases") y no vuelve a ejecutar `evaluar.py`:

```text
1. ¿Están al día los resultados grabados?
   huella guardada 7097dd989233952d · huella actual 862b0e86be161712
   FALLA: resultados desactualizados: vuelve a ejecutar evaluar.py
```

El control no sabe si el cambio mejora o empeora el sistema. Sabe que las respuestas grabadas ya no son las de este prompt, y no compara nada hasta que lo sean.

### Una regresión que el total no cuenta entera

Otro PR vuelve al prompt base con el modelo de 1,5B, para bajar la latencia. Esta vez sí repite la eval, así que la huella cuadra. El control lo compara con el último commit de `main` (`--contra HEAD`):

```text
1. ¿Están al día los resultados grabados?
   huella guardada e959fca61afd826d · huella actual e959fca61afd826d

2. Respuestas grabadas, repuntuadas con los comprobadores actuales
   42 de 58

3. Frente a HEAD
   52 → 42 de 58 casos comunes
   gana [], pierde ['m3-05', 'm3-22', 'm3-30', 'n-06', 'n-13', 'n-16', 's-05', 's-06', 'f-02', 'g-03'], p = 0.00
   FALLA: menos aciertos que en HEAD
   FALLA: pierde casos críticos: ['g-03']
```

Falla por las dos reglas. La lista de casos perdidos dice qué se pierde, y encaja con las categorías del análisis de errores: los procedimientos condicionales (m3-05, m3-22), las fuentes contradictorias (n-06), las preguntas que debían rechazarse (m3-30, s-06, f-02 y, en prueba, s-05) y el guardarraíl g-03. Si el equipo decide que la latencia compensa, la decisión se toma mirando esta lista, no un "42 frente a 52".

Fíjate también en que no gana ningún caso. En la primera versión de esta demo aparecían como ganados m3-09 y n-02, pero no porque la base respondiera mejor: eran las dos limitaciones del comprobador que encontró la lección 06, que aprobaba la frase larga de la base y suspendía la respuesta correcta y corta del sistema vigente. Corregido el comprobador, desaparecen. Un control automático hereda los defectos de sus comprobadores, y por eso conviene leer la lista de casos, no solo el veredicto.

### Qué cuesta la huella

La huella incluye `config/models.toml` entero. Si alguien cambia el modelo de otro módulo, el control de este falla y obliga a repetir la eval, aunque el sistema vigente no haya cambiado. Es una falsa alarma, y es una decisión consciente: incluir de más produce falsas alarmas, e incluir de menos deja pasar resultados desactualizados. Para un control de regresiones, lo segundo es peor. Si las falsas alarmas se vuelven frecuentes, la solución es afinar la huella (por ejemplo, solo los roles que usa el sistema), no quitarla.

## Errores frecuentes

**Ejecutar la eval con modelos en cada PR.** Es lenta, cara y no determinista: acabarás con un CI que falla por ruido y que el equipo aprende a ignorar. En cada PR, lo determinista; la eval completa, aparte.

**Grabar resultados sin saber de qué código salen.** Sin huella, un prompt cambiado y unas respuestas viejas pasan el CI en verde.

**Bloquear solo por el total.** Un cambio puede subir el total y perder un guardarraíl. Marca qué casos son críticos y no toleres perderlos.

**Comparar con comprobadores distintos.** Si la base se puntuó con el comprobador antiguo y la versión nueva con el actual, cualquier cambio del comprobador parece un cambio del sistema. Puntúa las dos versiones con el mismo.

**Ajustar el umbral hasta que el PR pase.** Las reglas se deciden antes de ver el resultado. Si una regla da falsos fallos, cámbiala en un PR aparte, justificándolo.

### Anatomía de un error: "desactualizados" en un PR que no toca el sistema

```text
1. ¿Están al día los resultados grabados?
   huella guardada 7097dd989233952d · huella actual 862b0e86be161712
   FALLA: resultados desactualizados: vuelve a ejecutar evaluar.py
```

**Cómo leerlo.** El control se ha parado en el paso 1: no ha comparado ninguna respuesta. Dice que alguno de los ficheros de los que dependen las respuestas ha cambiado desde que se grabaron. Aquí fue el prompt. Pero el mismo fallo sale si el PR solo cambia, por ejemplo, el modelo de embeddings de otra práctica en `config/models.toml`.

**Causa.** La huella cubre una lista de ficheros (`evaluar.ficheros()`), y basta con que cambie un byte de cualquiera de ellos. El control no sabe si ese byte afecta a las respuestas. Por eso pide repetir la eval en lugar de dar por buenas unas respuestas que quizá ya no lo son.

**Solución.** Mira qué fichero de la lista toca el PR (`git diff --stat main` contra `evaluar.ficheros()`). Si el cambio afecta al sistema vigente, ejecuta `evaluar.py` y sube el nuevo `vigente.jsonl`: el control lo comparará con la base. Si no le afecta, repítela igualmente: saldrán las mismas respuestas y la nueva huella. Si esto pasa a menudo, es la señal para afinar qué cubre la huella.

## Para profundizar

- [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions), y la guía de [seguridad de GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions) sobre la interpolación de expresiones en scripts.
- [Self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners) en la documentación de GitHub.
- Breck et al., [The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/) (2017). Qué comprobar de forma automática en un sistema con modelos.
- Ribeiro et al., [Beyond Accuracy: Behavioral Testing of NLP Models with CheckList](https://arxiv.org/abs/2005.04118) (2020). Casos de prueba por capacidad, la idea detrás de marcar casos críticos.

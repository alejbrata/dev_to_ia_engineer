---
title: "Métricas deterministas"
description: "Comprobaciones que no necesitan un modelo: cómo escribirlas sin falsos positivos, cómo recalcularlas sobre resultados grabados y cuánto margen de error tienen"
---

:::note[Revisado: 2026-10]
La práctica no llama a ningún modelo: trabaja sobre los resultados grabados en las lecciones 01 y 02 (Qwen2.5 1.5B Instruct y bge-m3 en Ollama).
:::

## Objetivos

Al terminar esta lección podrás:

- Elegir comprobaciones deterministas para un sistema con LLMs y saber qué mide cada una.
- Escribir comprobaciones de texto sin los falsos positivos habituales (números dentro de otros números, decimales, raíces de palabras).
- Recalcular las métricas sobre resultados grabados, sin volver a llamar al modelo.
- Dar una tasa de acierto con su intervalo de confianza y comprobar si la diferencia entre dos versiones es real.

## Teoría

### Qué es una métrica determinista

Una comprobación que, dada la misma respuesta, da siempre el mismo veredicto, y que se calcula con código, sin un modelo de por medio. Son baratas, rápidas y no se equivocan de forma impredecible: si fallan, fallan siempre igual, y se pueden depurar como cualquier otro código.

Las habituales en un sistema con LLMs:

| Comprobación | Qué mide | Ejemplo en el curso |
| --- | --- | --- |
| Coincidencia exacta | la respuesta es exactamente la esperada | la categoría de un ticket (módulo 2) |
| Contiene el dato | la respuesta incluye el dato clave | "200", "pagos/banco/token" |
| Abstención | dice que no lo sabe | "No aparece en la documentación" |
| Formato | es JSON válido y cumple el esquema | `RespuestaCitada` (módulo 3) |
| Citas | los números citados existen y apuntan al fragmento correcto | lección 06 del módulo 3 |
| Prohibido | no aparece algo que no debe aparecer | `PWNED` en un guardarraíl |
| Longitud, tokens, latencia, coste | límites operativos | "dos o tres frases como máximo" |
| Recuperación | recall@k, precision@k, MRR | lecciones 02-05 del módulo 3 |

No cubren todo. No pueden decidir si una explicación es correcta si está redactada de otra forma, ni si una respuesta es fiel al contexto: para eso hace falta un juez (lección 04). Pero cubren más de lo que parece, y todo lo que puedan cubrir debe ir con ellas.

### Escribir bien una comprobación de texto

"¿Contiene el dato?" parece trivial y tiene trampas:

- **Números dentro de otros números.** "4 horas" está dentro de "24 horas"; "99,9" está dentro de "99,95"; "3" está dentro de "30 minutos".
- **Formas de escribir lo mismo.** "tres" y "3", "02:00" y "2:00", "Cobros" y "cobros", "días" y "dias", "99,5" y "99.5".
- **Raíces de palabras.** Para aceptar "revócalo", "revocar" y "revocado", el dato clave es "revoc". Ahí no se puede exigir que la palabra termine.

En [`dataset.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/dataset.py), `contiene` normaliza el texto (minúsculas, sin tildes, coma decimal como punto), acepta alternativas (`"tres|3"`) y exige límites: el dato no puede ir pegado a otras letras o cifras por delante, y si acaba en cifra, tampoco puede seguir con más cifras por detrás. `contiene_subcadena` es la versión ingenua, que se queda en la práctica para comparar.

Una comprobación de texto es código, y se prueba como código. `test_dataset.py` tiene un test con los casos difíciles: "24 horas", "99,95 %", "10%" (debe aceptarse), "Revócalo".

### Guardar las salidas, recalcular las métricas

Como el informe guarda el texto de cada respuesta (lección 01), cualquier métrica determinista se puede recalcular cuando quieras: si corriges un comprobador, si añades una comprobación nueva o si cambias un dato clave del dataset. No hace falta volver a llamar al modelo, que es lo lento y, con un proveedor en la nube, lo caro. `datasets.py --grabadas` y `metricas.py` hacen exactamente eso.

### El margen de error

Un 67 % con 42 preguntas no es lo mismo que un 67 % con 400. Con pocos casos, un par de respuestas que salgan de otra forma mueven mucho el porcentaje. El **intervalo de confianza** dice entre qué valores está, razonablemente, la tasa de acierto real del sistema. `curso_core.evals.intervalo_wilson` calcula el de Wilson, que funciona bien con pocos casos y con tasas cerca de 0 % o de 100 %.

Para comparar dos versiones sobre los mismos casos hay una herramienta mejor que comparar sus intervalos: mirar solo los casos en los que **discrepan**. Si las dos versiones fueran igual de buenas, cada discrepancia caería a favor de una u otra al 50 %, como una moneda. La **prueba de McNemar** (`prueba_mcnemar`) calcula la probabilidad de ver un reparto tan desigual como el observado si fueran igual de buenas: el p-valor. Si es alto, la diferencia es compatible con el azar.

No hace falta más estadística para empezar. Hace falta acostumbrarse a dar cada número con su margen.

## Práctica

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/metricas.py
```

[`metricas.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/04-evals/metricas.py) trabaja sobre los resultados grabados en `modulos/04-evals/resultados/` y no llama al modelo. Tarda menos de un segundo:

```text
1. Las respuestas grabadas, puntuadas con los dos comprobadores
   n-07: bien → MAL  ['4 horas', 'dos personas']  'La restauración tardó aproximadamente 24 horas. Después de este incide'
   veredictos que cambian: 1 de 58

2. Otras comprobaciones deterministas (dataset anclado)
   se abstienen:                 11 de 58
   contestan sin citar nada:     0 de 47
   citas fuera de [1, 3]:        0 de 68
   palabras por respuesta:       mediana 17, máximo 68
   más de 60 palabras (pide 2-3 frases): ['m3-01', 'm3-24']

3. Tasas de acierto con su intervalo de confianza del 95 %
   con respuesta                28 de 42   67%   [ 52%,  79%]
   no deben responderse          9 de 16   56%   [ 33%,  77%]
   partición desarrollo         26 de 39   67%   [ 51%,  79%]
   partición prueba             11 de 19   58%   [ 36%,  77%]
   etiqueta parafrasis           1 de  3   33%   [  6%,  79%]

4. Lección 01: ¿es real la diferencia entre las dos versiones?
   v1-texto-libre               18 de 30   60%   [ 42%,  75%]
   v2-con-citas                 20 de 30   67%   [ 49%,  81%]
   discrepancias: gana 2, pierde 0 → p = 0.50
   si ganara 3 y no perdiera ninguna → p = 0.250
   si ganara 4 y no perdiera ninguna → p = 0.125
   si ganara 5 y no perdiera ninguna → p = 0.062
   si ganara 6 y no perdiera ninguna → p = 0.031
   si ganara 7 y no perdiera ninguna → p = 0.016

5. Margen de error (mitad del intervalo) con una tasa del 67 %, según el número de casos
    19 casos: ±19.3%
    42 casos: ±13.7%
   100 casos: ±9.1%
   200 casos: ±6.5%
   400 casos: ±4.6%
```

## Mide y depura

### Un falso positivo en 58 casos

Con el comprobador ingenuo, la pregunta n-07 (*¿cuánto tardó la restauración del incidente de usuarios y qué regla se añadió después?*) contaba como acierto. La respuesta dice "aproximadamente 24 horas"; fueron 4. El comprobador buscaba "4 horas" y lo encontraba dentro de "24 horas". Con el comprobador corregido, la pregunta pasa a fallo y las preguntas con respuesta bajan de 29 a 28 aciertos. Las cifras de la lección 02 ya están corregidas.

Un caso de 58 parece poco. Pero es un fallo que **infla** el resultado, y lo hace justo en las respuestas que se equivocan por poco, que son las más difíciles de ver leyendo por encima. Y en datasets con más números (precios, plazos, umbrales) aparece más.

El comprobador del módulo 3 (`corpus.es_correcta`) tiene el mismo defecto. En las respuestas de la lección 01 no produjo ningún falso positivo, así que esas cifras no cambian; el dataset de este módulo ya usa el corregido.

### Otras comprobaciones que no cuestan nada

Sobre las mismas respuestas, sin modelo: todas las que contestan citan algo, y ninguna cita un fragmento que no existe. En cambio, dos respuestas superan las 60 palabras cuando el prompt pide "dos o tres frases como máximo". Es una comprobación de longitud trivial que detecta que el modelo no siempre sigue esa instrucción. Si en tu sistema la longitud importa (una interfaz pequeña, un coste por token), mídela.

### Los intervalos son anchos

- **28 de 42 con respuesta, 67 %**: el valor real puede estar entre el 52 % y el 79 %. Es la precisión que da un dataset de 42 casos.
- **Desarrollo frente a prueba**: 67 % y 58 %. Los intervalos, [51 %, 79 %] y [36 %, 77 %], se solapan casi por completo. No hay indicio de que el sistema vaya peor en prueba; con 19 casos no se puede saber.
- **Paráfrasis, 1 de 3**: entre el 6 % y el 79 %. Un desglose por etiqueta con 3 casos sirve para encontrar ejemplos de fallos, no para medir.

### ¿Era real la mejora de la lección 01?

La versión con citas ganó 2 preguntas y no perdió ninguna. El p-valor de McNemar es 0,50: si las dos versiones fueran igual de buenas, un 2 a 0 saldría la mitad de las veces. Con 2 discrepancias no se puede afirmar que la versión con citas sea mejor. Para llegar al umbral habitual (p < 0,05) haría falta que ganara 6 sin perder ninguna.

Eso no quiere decir que el cambio no sirva. Quiere decir que este dataset no basta para demostrarlo. Hay dos salidas: más casos, sobre todo del tipo en el que se espera que el cambio influya (aquí, preguntas sin respuesta), o aceptar la decisión con la evidencia que hay sabiendo que es débil. Lo que no vale es presentar "18 frente a 20" como una mejora demostrada.

### Cuántos casos hacen falta

Con una tasa en torno al 67 %, el margen de error es de ±19 puntos con 19 casos, ±14 con 42, ±9 con 100 y ±5 con 400. Para detectar mejoras de pocos puntos hacen falta cientos de casos. Por eso conviene que las comprobaciones sean deterministas siempre que se pueda: con un juez, cada caso cuesta una llamada más a un modelo grande.

## Errores frecuentes

**Buscar el dato como subcadena.** Es el error de esta lección. Exige límites, sobre todo con números.

**No probar el comprobador.** Una función que decide si el sistema acierta necesita sus propios tests, con los casos difíciles.

**Dar porcentajes sin el número de casos.** "67 %" no dice nada sin "de 42". Mejor aún, con su intervalo.

**Comparar versiones por el total.** Compara caso a caso y mira las discrepancias. 20 frente a 18 puede ser 2 a 0 o 10 a 8, y no significan lo mismo.

**Sacar conclusiones de desgloses pequeños.** Un 33 % en 3 casos es una pista para buscar ejemplos, no una medida.

### Anatomía de un error: el acierto que tardó 24 horas

```text
n-07: bien → MAL  ['4 horas', 'dos personas']  'La restauración tardó aproximadamente 24 horas. …'
```

**Cómo leerlo.** El caso pide dos datos: cuánto tardó la restauración (4 horas, según el postmortem de usuarios) y qué regla se añadió (la aprobación de dos personas). La respuesta da bien la regla y mal el tiempo: 24 horas. Con el comprobador ingenuo, la eval la daba por buena. Con el corregido, no.

**Causa.** `contiene_subcadena` busca "4 horas" en cualquier posición del texto, y "24 horas" lo contiene. No había ningún error ni aviso: el número salía un punto más alto y parecía normal.

**Solución.** Exigir límites en las comprobaciones de texto: que el dato no vaya pegado a otras cifras o letras. Escribir un test con los casos difíciles ("24 horas", "99,95 %") para que el comprobador no vuelva a romperse. Y, como las respuestas están guardadas, repuntuar todos los resultados anteriores con el comprobador corregido, sin volver a llamar al modelo.

## Para profundizar

- Miller, [Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations](https://arxiv.org/abs/2411.00640) (2024). Intervalos de confianza y comparaciones por pares aplicados a evals de modelos de lenguaje.
- [Binomial proportion confidence interval](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval) en Wikipedia: el intervalo de Wilson y por qué es mejor que el "normal" con pocos casos.
- [McNemar's test](https://en.wikipedia.org/wiki/McNemar%27s_test) en Wikipedia: comparar dos clasificadores sobre los mismos casos.

---
title: "Qué hace un AI Engineer (y qué no)"
description: "Qué hace un AI Engineer (y qué no): frente a ML Engineer, Data Scientist y dev \"que usa IA\""
---

## Objetivos

Al terminar esta lección podrás:

- Explicar en dos frases qué diferencia a un AI Engineer de un ML Engineer y de un Data Scientist.
- Clasificar tareas habituales según el rol al que pertenecen.
- Nombrar las cuatro métricas que este curso mide en todos los módulos.
- Explicar por qué la salida de un LLM no se puede tratar como la de una función determinista.

## Teoría

### El punto de partida: el modelo ya existe

Durante años, usar machine learning en un producto exigía entrenar un modelo propio. Necesitabas datos etiquetados, infraestructura de entrenamiento y gente que supiera hacerlo. Los grandes modelos de lenguaje (LLMs) cambiaron ese punto de partida. Hoy hay modelos generales, ya entrenados, a los que llamas por API o que descargas y ejecutas tú.

El trabajo se desplaza. La pregunta deja de ser "¿cómo entreno un modelo que haga esto?" y pasa a ser "¿cómo construyo un sistema fiable alrededor de un modelo que ya existe?". De ese desplazamiento nace el rol de **AI Engineer**. El término se popularizó en 2023 con el artículo de swyx enlazado al final.

### Cuatro perfiles que se confunden

**Data Scientist.** Analiza datos para responder preguntas de negocio. Diseña experimentos, construye modelos estadísticos y comunica conclusiones. Su entregable suele ser una decisión o un informe, no un servicio en producción.

**ML Engineer.** Entrena, despliega y mantiene modelos propios. Se ocupa de pipelines de datos, features, entrenamiento, serving y reentrenamiento (lo que se suele llamar MLOps). Su entregable es un modelo funcionando en producción.

**AI Engineer.** Construye producto sobre modelos ya entrenados. Diseña prompts y contexto, conecta el modelo con datos propios (RAG) y con herramientas (agentes), y mide la calidad con evals. También controla coste, latencia y errores en producción. A veces ajusta un modelo (fine-tuning), pero rara vez entrena uno desde cero. Su entregable es un sistema que funciona y del que sabe cuánto funciona.

**Dev "que usa IA".** Hay dos variantes. Una usa asistentes de código para programar más rápido. La otra integra una llamada a un LLM en su aplicación y da el trabajo por terminado cuando la demo sale bien. Las dos son útiles, pero no son el puesto. La diferencia está en lo que viene después de la demo: medir, depurar y sostener el sistema cuando el modelo se equivoca.

### Qué no hace un AI Engineer

- No investiga arquitecturas de modelos ni entrena modelos fundacionales. Eso es investigación y requiere otro perfil y otro presupuesto.
- No se limita a escribir prompts. El prompt es una pieza más, como lo es una consulta SQL en un backend.
- No trata el modelo como un oráculo. Lo trata como una dependencia externa que a veces falla, y diseña el sistema para que eso no lo rompa.

### Por qué un backend lo tiene más cerca de lo que cree

Si vienes de backend, ya conoces la mitad del trabajo. Integrar un LLM se parece a integrar un servicio de terceros con un SLA poco fiable. Hay que poner timeouts y reintentos, validar lo que devuelve, registrar cada llamada y vigilar el coste.

La diferencia está en la otra mitad. Un servicio REST mal implementado falla siempre igual. Un LLM puede devolver una respuesta correcta nueve veces y una incorrecta la décima, con la misma entrada. Por eso la calidad no se comprueba con un test unitario y ya. Se mide con muchos casos y se vigila en el tiempo.

## Práctica

Esta lección no tiene código. La práctica es un ejercicio de clasificación.

Asigna cada tarea al rol que más encaja: Data Scientist (DS), ML Engineer (MLE) o AI Engineer (AIE).

1. Entrenar un modelo de detección de fraude con el histórico de transacciones del banco.
2. Montar un asistente que responde dudas internas usando la documentación de la empresa.
3. Analizar si una campaña de marketing ha subido las ventas.
4. Medir con 200 casos si un cambio de prompt empeora las respuestas de un chatbot.
5. Reentrenar cada mes un modelo de recomendación y desplegarlo sin cortes.
6. Reducir a la mitad el coste por petición de un servicio que llama a un LLM.

<details>
<summary>Solución</summary>

1. MLE: entrena un modelo propio con datos propios.
2. AIE: RAG sobre un modelo ya entrenado.
3. DS: análisis causal para tomar una decisión.
4. AIE: evals de un sistema basado en LLM.
5. MLE: ciclo de vida de un modelo propio (MLOps).
6. AIE: optimización operativa de un sistema con LLM.

Algunas tareas están en la frontera. El fine-tuning, por ejemplo, lo pueden hacer los dos perfiles de ingeniería. Lo útil no es la etiqueta, sino saber qué habilidades pide cada tarea.

</details>

## Mide y depura

Lo que separa al AI Engineer del dev "que usa IA" es que mide. En este curso medirás estas cuatro métricas en todos los módulos, a partir del módulo 1:

| Métrica | Qué es | Equivalente en backend |
| --- | --- | --- |
| Tokens | Unidades de texto que entran y salen del modelo. Determinan el coste y el límite de contexto. | Tamaño de payload |
| Latencia | Tiempo hasta la respuesta completa y, en streaming, hasta el primer token. | Tiempo de respuesta en tu APM |
| Coste | Precio de cada llamada, calculado a partir de los tokens. | Coste por petición de un servicio de pago |
| Tasa de error | Llamadas que fallan, tanto por errores técnicos como por respuestas inválidas. | Tasa de errores 5xx |

La última fila tiene trampa. En un backend, un error suele ser una excepción. Con un LLM, también es error una respuesta que llega bien pero no sirve: un JSON mal formado, un dato inventado o un formato que no pediste. Medir eso es el tema del módulo 4.

## Errores frecuentes

**Creer que el puesto exige entrenar modelos.** La mayor parte del trabajo es ingeniería de software alrededor de un modelo existente. Las matemáticas que necesitas son pocas y se explican cuando hacen falta.

**Confundir una demo con un producto.** Que funcione con los cinco ejemplos que has probado no dice nada de los cinco mil que llegarán en producción. "Parece que funciona" no es una métrica.

**Tratar la salida del modelo como la de una función.** Es el error más común al empezar. Lo ves en detalle abajo.

### Anatomía de un error: el JSON que no era JSON

Pides al modelo que devuelva el sentimiento de un texto en JSON y parseas la respuesta directamente:

```python
import json

respuesta = llamar_al_modelo(prompt)  # lo que devolvió el modelo
datos = json.loads(respuesta)
```

Casi siempre funciona. Hasta que un día falla:

```text
Traceback (most recent call last):
  ...
  File "C:\Python313\Lib\json\decoder.py", line 363, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Cómo leerlo.** La última línea es la que importa. `Expecting value` significa que el parser esperaba el comienzo de un valor JSON (`{`, `[`, un número…). `line 1 column 1 (char 0)` dice dónde: en el primer carácter. El texto no empieza como un JSON.

**Causa.** Al imprimir la respuesta, ves esto:

```text
Claro, aquí tienes el JSON:
{"sentimiento": "positivo"}
```

El modelo ha añadido una frase de cortesía antes del JSON. No es un bug del modelo: es un sistema probabilístico, y "casi siempre en el formato pedido" no es "siempre".

**Solución.** No confíes en el formato; contrólalo y valídalo. Los proveedores ofrecen salida estructurada, que restringe la respuesta a un esquema. Además, valida siempre lo que llega y decide qué hacer si falla: reintentar, corregir o registrar el error. Lo verás a fondo en [Salida estructurada](../../02-prompting/03-salida-estructurada/).

La lección general sirve para todo el curso: cada vez que uses la salida de un modelo, pregúntate qué pasa si no viene como esperas.

## Bitácora

TODO(alex)

## Para profundizar

- swyx, [The Rise of the AI Engineer](https://www.latent.space/p/ai-engineer) (2023). El artículo que popularizó el término.
- Chip Huyen, [*AI Engineering*](https://huyenchip.com/books/) (O'Reilly, 2025). Libro de referencia sobre el rol y sus técnicas.
- Sculley et al., [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html) (NeurIPS 2015). Por qué el modelo es la parte pequeña de un sistema de ML.
- Hamel Husain, [Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/). Por qué medir es el centro del trabajo.

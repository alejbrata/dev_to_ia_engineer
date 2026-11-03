---
title: "Reto del módulo: la alerta de las 3:00"
description: "Reto del módulo 6, sin solución guiada: con las peticiones de dos noches sacadas de las trazas, escribir una alerta que no salte por ruido, que vea una degradación silenciosa desde la primera ventana, y encontrar su causa"
---

Tienes una alerta con fallos, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio: ábrela al final, para comparar.

## Objetivos

- Leer las señales de un servicio de LLM por ventanas de tiempo y distinguir el ruido de un incidente.
- Encontrar una degradación silenciosa (sin errores y sin más latencia) en los atributos de las trazas.
- Escribir una alerta que salte cuando hace falta y no cuando no, y comprobarla contra los datos.

## El reto

La segunda noche, desde las 3:00, el asistente empezó a responder mal y nadie se enteró hasta la mañana: no saltó ninguna alerta. La primera noche, en cambio, la alerta despertó a la persona de guardia varias veces y no pasaba nada grave.

[`reto/peticiones.jsonl`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/06-produccion/reto/peticiones.jsonl) tiene las peticiones de esas dos noches, de 0:00 a 6:00, sacadas de las trazas (lección 02). Cada una lleva la hora, la latencia, si acabó en error, qué rol respondió, los tokens que mandó el cliente, los que procesó el servidor del modelo (`gen_ai.usage.input_tokens`) y si la respuesta fue una abstención:

```json
{"noche": 2, "hora": "03:00:00", "ms": 10118, "error": false, "rol": "chat_grande", "tokens_enviados": 1623, "tokens_procesados": 1024, "abstencion": true}
```

[`reto/alerta.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/06-produccion/reto/alerta.py) agrupa las peticiones en ventanas de 10 minutos, calcula sus señales, decide en cuáles salta la alerta y da una causa. Un trozo de su salida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/06-produccion/reto/alerta.py
```

```text
noche 1
          pet.  errores  abstenc.  respaldo     p95
   00:40    34       3%       12%        0%   15.3s ALERTA
   00:50    28       4%        7%        0%   14.4s ALERTA
   01:00   101       6%       14%        1%   20.1s ALERTA
   01:10    97       5%       12%        1%   21.6s ALERTA
   01:20    27       0%        7%        0%   14.8s
...
noche 2
   02:50    30       3%       10%        3%   16.8s ALERTA
   03:00    33       3%       45%        0%   12.5s ALERTA
   03:10    26       0%       54%        4%   13.0s
   03:20    31       0%       48%        0%   12.9s
...
causa: más tráfico del habitual
```

Arregla la alerta y cambia `CAUSA` por una de las de `CAUSAS`, la que expliquen los datos. Puedes añadir señales a las ventanas y cambiar la regla, pero no las peticiones.

## Criterios de aceptación

1. La primera noche, que es normal, la alerta no salta en ninguna ventana. Tampoco en el pico de tráfico de la 1:00: dura 20 minutos, se recupera solo y no justifica despertar a nadie.
2. La segunda noche no salta antes de las 3:00.
3. Salta en la primera ventana del incidente, la de las 3:00.
4. Salta en al menos 16 de las 18 ventanas del incidente.
5. `CAUSA` es la que explican los datos.

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/06-produccion/reto/comprobar.py) pasa tu alerta por todas las ventanas de las dos noches. No llama a ningún modelo. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/06-produccion/reto/comprobar.py
```

```text
Reto del módulo 6 · reto/alerta.py
   FALLA la primera noche, normal, no salta (tampoco en el pico de tráfico): salta a las 00:40, 00:50, 01:00, 01:10, 05:00
   FALLA la segunda noche no salta antes del incidente: salta a las 02:10, 02:20, 02:30, 02:50
   OK    salta en la primera ventana del incidente
   FALLA salta en al menos 16 de las 18 ventanas del incidente: 4 de 18
   FALLA la causa es la que explican los datos: devuelve 'más tráfico del habitual'
1 de 5 criterios. Sigue: lee el primero que falla.
```

El criterio 3 lo cumple por casualidad: a las 3:00 hubo un error suelto. El reto está superado cuando dice `Reto superado: 5 de 5 criterios.`.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: el ruido</summary>

¿Cuántas peticiones hay en una ventana normal? Con ese número, ¿qué porcentaje de errores es un solo error? Una alerta que salta por un error suelto acaba sin que nadie la mire.

</details>

<details>
<summary>Pista 2: qué cambia a las 3:00</summary>

Compara las columnas antes y después de las 3:00 en la segunda noche. Los errores no cambian, y la latencia baja. ¿Qué sube? ¿Bastaría con poner un umbral a esa señal, viendo cuánto llega a valer en las noches normales?

</details>

<details>
<summary>Pista 3: la causa</summary>

Hay un campo de las peticiones que `ventanas` no usa. Compara `tokens_enviados` y `tokens_procesados` antes y después de las 3:00, y relee qué hacía Ollama en la lección 1.02 cuando el prompt no cabía.

</details>

## La solución

Está en [`reto/solucion/alerta.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/06-produccion/reto/solucion/alerta.py), con los tres cambios marcados, y se comprueba con `comprobar.py --solucion`:

```text
Reto del módulo 6 · reto/solucion/alerta.py
   OK    la primera noche, normal, no salta (tampoco en el pico de tráfico)
   OK    la segunda noche no salta antes del incidente
   OK    salta en la primera ventana del incidente
   OK    salta en al menos 16 de las 18 ventanas del incidente: 18 de 18
   OK    la causa es la que explican los datos
Reto superado: 5 de 5 criterios.
```

La solución añade a cada ventana una señal, la fracción de peticiones en las que el servidor procesó menos tokens de los que se le mandaron:

```text
          pet.  errores  abstenc.  respaldo     p95  recort.
   02:50    30       3%       10%        3%   16.8s       0%
   03:00    33       3%       45%        0%   12.5s      94% ALERTA
   03:10    26       0%       54%        4%   13.0s     100% ALERTA
```

Desde las 3:00, el servidor del modelo principal procesa como mucho 1.024 tokens de prompts de unos 1.500. Es el recorte silencioso de la lección 1.02: descarta el principio del prompt (las reglas y los primeros fragmentos) y sigue sin avisar. El modelo responde sin su contexto y se abstiene en la mitad de las preguntas. No hay errores, y la latencia baja, porque hay menos que procesar. Por eso ninguna alerta de las habituales lo veía.

- **La señal está en la traza, no en el resultado.** Las abstenciones suben, pero una alerta sobre ellas es frágil: en las noches normales llegan al 30 % en alguna ventana, y en el incidente bajan hasta el 33 %. El recorte, en cambio, es 0 % en una noche normal y más del 90 % en el incidente. Si registras los tokens procesados (lección 02), cuesta una línea vigilarlo. Si no, no hay forma de verlo.
- **Una alerta que salta por ruido se deja de mirar.** Con unas 30 peticiones por ventana, un solo error es un 3 %, y la regla de partida saltaba nueve veces en noches tranquilas. Una alerta de errores sigue haciendo falta, pero con un umbral y una ventana que no salten por un error suelto ni por un pico que se recupera solo (lección 03).
- **La causa no es lo que dice el panel más llamativo.** El pico de la 1:00 tenía el triple de tráfico, la latencia más alta de las dos noches y errores, y no era el problema. Es la lección 07 en pequeño: la señal que grita no siempre es la que importa.

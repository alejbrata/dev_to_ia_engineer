---
title: "Reto del módulo: la factura que subió"
description: "Reto del módulo 1, sin solución guiada: con el log de dos semanas de un asistente, calcular bien el coste y la latencia, encontrar el día en que algo cambió y explicar por qué subió la factura"
---

Tienes un script con fallos, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio: ábrela al final, para comparar.

## Objetivos

- Calcular el coste de una llamada con precios distintos de entrada y de salida, y una p95 bien calculada.
- Separar un cambio de volumen (más llamadas) de un cambio en cada llamada (más tokens por llamada).
- Encontrar en un log la causa de una subida de coste y apoyarla en una cifra.

## El reto

La segunda semana, el asistente de soporte costó bastante más que la primera. Producto cree que es por la campaña del día 4, que trajo mucho tráfico. [`reto/llamadas.jsonl`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/reto/llamadas.jsonl) es una muestra del log de esas dos semanas: una línea por llamada al modelo, con el día, la sesión, el turno de la conversación, los tokens de entrada y de salida y la latencia.

```json
{"dia": "2026-10-01", "sesion": "1001-000", "turno": 1, "tokens_entrada": 475, "tokens_salida": 157, "ms": 4430}
```

Los precios del reto están en `reto/precios.toml`: 3 $ por millón de tokens de entrada y 12 $ por millón de salida. Son inventados, con la proporción habitual entre entrada y salida (lección 06).

[`reto/factura.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/reto/factura.py) calcula el coste y la latencia por día, busca el día en que algo cambió y da una causa. Su salida empieza y acaba así:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/reto/factura.py
```

```text
día           llamadas     coste  por llamada      p95
2026-10-01          77    0.700$     9.097 m$     4.3s
2026-10-02          74    0.665$     8.989 m$     4.4s
...
semana primera: 604 llamadas, 5.47 $
semana segunda: 516 llamadas, 8.43 $
día del cambio: 2026-10-04
...
causa: más tráfico
```

Le da la razón a producto, y se equivoca: en las cifras, en el día y en la causa. Arréglalo hasta que cumpla los criterios, y cambia `CAUSA` por una de las cuatro de `CAUSAS`, la que expliquen los datos.

## Criterios de aceptación

1. Una llamada de 1.000 tokens de entrada y 100 de salida cuesta 0,0042 $.
2. El coste total de las dos semanas es el que sale de esos precios.
3. La p95 de 20 valores ordenados es el 19.º (percentil por rango).
4. La p95 de una lista es la misma esté ordenada o no.
5. El detector señala el día en que de verdad cambió algo.
6. En la primera semana, sola, el detector no señala ningún día: la campaña trae más tráfico, pero no cambia nada más.
7. `CAUSA` es la que explican los datos.

No cambies las firmas de las funciones: el comprobador las llama tal como están.

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/reto/comprobar.py) prueba tus funciones con el log y con casos pequeños. No llama a ningún modelo. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/01-fundamentos-de-llms/reto/comprobar.py
```

```text
Reto del módulo 1 · reto/factura.py
   FALLA una llamada de 1.000 tokens de entrada y 100 de salida cuesta 0,0042 $: devuelve 0.0132, se esperaba 0.0042
   FALLA las dos semanas del log cuestan 4.9726 $: devuelve 13.899036, se esperaba 4.972602
   OK    la p95 de 20 valores ordenados es el 19.º
   FALLA la p95 de 1 a 100, desordenados, es 95: devuelve 66, se esperaba 95
   FALLA el detector señala el día en que de verdad cambió algo: devuelve '2026-10-04'
   FALLA en la primera semana no hay cambio: la campaña del día 4 trae más tráfico, nada más: devuelve '2026-10-04', se esperaba None
   FALLA la causa es la que explican los datos: devuelve 'más tráfico'
1 de 7 criterios. Sigue: lee el primero que falla.
```

Los dos últimos no dicen qué se esperaba: la respuesta es el reto. El reto está superado cuando dice `Reto superado: 7 de 7 criterios.`.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: el coste</summary>

Mira qué hace `coste` con `precios["entrada"]`. Y, con el coste arreglado, compara la columna "por llamada" de la primera semana con la de la segunda.

</details>

<details>
<summary>Pista 2: el día del cambio</summary>

El día 4 es el más caro de todos. ¿Cuesta más cada llamada, o hay más llamadas? Un detector que mira el total confunde las dos cosas.

</details>

<details>
<summary>Pista 3: la causa</summary>

`factura.py` ya imprime los tokens de entrada por turno, antes y después del día que detecta. Con el día bien detectado, ¿qué pasa con esos tokens a medida que avanza la conversación? Relee en la lección 04 qué tiene que mandar el cliente en cada llamada para que el modelo "recuerde".

</details>

## La solución

Está en [`reto/solucion/factura.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/01-fundamentos-de-llms/reto/solucion/factura.py), con los cuatro cambios marcados, y se comprueba con `comprobar.py --solucion`. Con ella, la factura queda así:

```text
2026-10-04         187    0.675$     3.607 m$     5.4s
2026-10-07          67    0.239$     3.571 m$     5.4s
2026-10-08          78    0.445$     5.700 m$     5.7s
semana primera: 604 llamadas, 2.17 $
semana segunda: 516 llamadas, 2.80 $
día del cambio: 2026-10-08
tokens de entrada por turno, antes y después del cambio:
   turno  1:     484     478
   turno  4:     627    1101
   turno  8:     635    1923
   turno 12:     630    2750
causa: el contexto crece con cada turno
```

La segunda semana tiene menos llamadas (516 frente a 604) y cuesta un 29 % más. El día 4 es el más caro, pero cada llamada cuesta lo mismo que cualquier otro día: es volumen. El día 8, en cambio, el coste por llamada salta de unos 3,6 a 5,7 milésimas de dólar, y no vuelve. Los tokens de entrada lo explican. Antes del día 8 se quedan en unos 630 en cualquier turno: el cliente mandaba un resumen corto de la conversación. Desde el día 8 crecen unos 200 por turno, hasta 2.750 en el turno 12. El cliente empezó a reenviar el historial entero (lección 04), y cada turno paga otra vez todos los anteriores.

Tres cosas que se llevan a cualquier sistema:

- **Normaliza antes de comparar.** El coste total sube con el tráfico. El coste por llamada, o por conversación, es el que dice si algo cambió en el sistema.
- **Un percentil sin ordenar es un número cualquiera.** El fallo no da error: da 66 donde había que dar 95.
- **La latencia no lo habría visto.** La p95 apenas cambia (de unos 5,4 a 5,7 segundos), porque aquí la marcan los tokens de salida. Una alerta de latencia se habría quedado callada. Vigila los tokens de entrada por llamada (lección 06) y no dejes crecer el historial sin control: recórtalo o resúmelo (lección 02).

---
title: "Reto del módulo: el agente que lo hace dos veces"
description: "Reto del módulo 5, sin solución guiada: la capa que ejecuta las acciones de un agente contra una API con fallos reales (timeouts después de actuar, 429, 400) y una acción destructiva que necesita aprobación humana"
---

Tienes un ejecutor con fallos, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio: ábrela al final, para comparar.

## Objetivos

- Reintentar sin duplicar acciones, con una clave de idempotencia, cuando no sabes si una acción se hizo.
- Distinguir los errores que se reintentan (timeout, 429) de los que no (400), y respetar un `Retry-After`.
- Poner la aprobación humana de una acción destructiva en el código, no en el prompt.

## El reto

El agente de guardia decide qué hacer: abrir una incidencia, avisar a un equipo, volver a la versión anterior de un servicio. [`reto/ejecutor.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/05-agentes/reto/ejecutor.py) lo hace contra la API de la plataforma. Es la capa entre el modelo y el mundo, y es donde se decide si una acción se repite, se espera o se pide permiso. Las lecciones 11 y 13 lo dejaban claro: un prompt puede pedirle al modelo que no repita una acción, pero solo el código puede garantizarlo.

La API es [`reto/api_simulada.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/05-agentes/reto/api_simulada.py), con los fallos de una API real, pero deterministas:

- **Timeout.** La petición no tiene respuesta a tiempo, aunque la acción sí se hizo. No sabes cuál de las dos cosas ha pasado.
- **429 con `Retry-After`.** Hasta que pasa ese tiempo, cada petición vuelve a dar 429.
- **400.** La petición es incorrecta, y repetirla da lo mismo.
- **Clave de idempotencia.** La API admite una: repetir una petición con la misma clave devuelve el resultado de la primera sin repetir la acción.
- **Una operación destructiva,** `volver_version_anterior`, que no tiene vuelta atrás.

No cambies `api_simulada.py` ni la firma de `ejecutar`. El ejecutor de partida reintenta tres veces cualquier error y nada más.

## Criterios de aceptación

El comprobador ejecuta cinco escenarios. Cada uno es una secuencia fija de acciones del agente, con una petición que falla:

| Escenario | Acciones del agente | Qué falla |
| --- | --- | --- |
| timeout al abrir la incidencia | abrir | la primera petición da timeout, después de abrirla |
| timeout al volver atrás, aprobado | abrir, volver atrás | volver atrás da timeout después de hacerlo; la persona de guardia aprueba |
| volver atrás, denegado | abrir, volver atrás | nada; la persona de guardia lo deniega |
| límite de uso al avisar | abrir, avisar | avisar da 429, con 2 segundos de `Retry-After` |
| severidad no válida | abrir con severidad "urgente", avisar | abrir da 400 |

Los criterios:

1. Ninguna acción se hace dos veces.
2. Cada acción se hace las veces que debía: una, o ninguna si se deniega o se rechaza.
3. Ninguna acción destructiva se hace sin la aprobación de una persona.
4. Si la persona la deniega, no se hace, y el resultado que lee el agente lo dice.
5. Después de un 429, no se repite la petición antes del `Retry-After`.
6. Un 400 no se reintenta.

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/05-agentes/reto/comprobar.py) ejecuta los escenarios con un reloj simulado: esperar no cuesta tiempo real. No llama a ningún modelo y tarda menos de un segundo. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/05-agentes/reto/comprobar.py
```

```text
Reto del módulo 5 · reto/ejecutor.py
   FALLA ninguna acción se hace dos veces: falla en: timeout al abrir la incidencia; timeout al volver atrás, aprobado
   FALLA cada acción se hace las veces que debía: una, o ninguna si se deniega o se rechaza: falla en: timeout al abrir la incidencia; timeout al volver atrás, aprobado; volver atrás, denegado; límite de uso al avisar
   FALLA ninguna acción destructiva sin la aprobación de una persona: falla en: timeout al volver atrás, aprobado; volver atrás, denegado
   FALLA si la persona la deniega, no se hace y el agente lo lee en el resultado: resultado: 'pagos: desplegada la versión anterior'
   FALLA después de un 429, no se repite antes del Retry-After: falla en: límite de uso al avisar
   FALLA un 400 no se reintenta: 3 peticiones con la misma severidad no válida
0 de 6 criterios. Sigue: lee el primero que falla.
```

El reto está superado cuando dice `Reto superado: 6 de 6 criterios.`.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: los duplicados</summary>

Tras un timeout, la acción puede haberse hecho. Reintentar está bien; lo que falta es que la API sepa que el reintento es la misma acción. ¿Qué acepta `ApiSimulada.llamar` además de la operación y los argumentos? ¿Qué tiene cada acción que sea único?

</details>

<details>
<summary>Pista 2: la aprobación</summary>

`api_simulada.py` define qué operaciones son destructivas. `ejecutar` recibe una función para preguntar a la persona de guardia, y nadie la llama. ¿Y qué debería leer el agente si la persona dice que no?

</details>

<details>
<summary>Pista 3: 429 y 400</summary>

No todos los errores son iguales. Uno dice cuánto esperar (`LimiteDeUso.espera`) y el reloj sabe esperar. Otro dice que la petición está mal, y repetirla tres veces da tres veces el mismo error.

</details>

## La solución

Está en [`reto/solucion/ejecutor.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/05-agentes/reto/solucion/ejecutor.py), con los cuatro cambios marcados, y se comprueba con `comprobar.py --solucion`:

```text
Reto del módulo 5 · reto/solucion/ejecutor.py
   OK    ninguna acción se hace dos veces
   OK    cada acción se hace las veces que debía: una, o ninguna si se deniega o se rechaza
   OK    ninguna acción destructiva sin la aprobación de una persona
   OK    si la persona la deniega, no se hace y el agente lo lee en el resultado: resultado: 'Acción denegada por la persona de guardia: volver_version_anterior no se ha hecho.'
   OK    después de un 429, no se repite antes del Retry-After
   OK    un 400 no se reintenta: 1 petición con la misma severidad no válida
Reto superado: 6 de 6 criterios.
```

Son pocas líneas, y cada cambio corresponde a un fallo que pasa en producción:

- **La clave de idempotencia es el id de la acción.** Con ella, reintentar tras un timeout es seguro: si la acción ya se hizo, la API devuelve el resultado de la primera vez. Sin ella, el código de partida abría dos incidencias y volvía atrás dos veces. La clave tiene que identificar la acción del agente, no la petición: cada reintento es una petición nueva de la misma acción. En la lección 13, la clave era el escenario y el servicio; aquí la da quien decide la acción.
- **La aprobación va antes de llamar, en código.** `DESTRUCTIVAS` es una lista explícita: una operación nueva no queda aprobada por defecto. Si la persona deniega, el ejecutor devuelve un texto que lo dice. Así el agente no da por hecha una vuelta atrás que no ocurrió, ni la vuelve a intentar con otras palabras.
- **Cada error se trata según lo que significa.** Un 429 se espera lo que dice `Retry-After`: el código de partida reintentaba al instante, cada reintento volvía a dar 429 y la acción se perdía. Un 400 se devuelve al agente sin reintentar, para que corrija el argumento.
- **El agente lee el resultado.** Todo lo que devuelve `ejecutar` acaba en el contexto del modelo como resultado de la herramienta. Un "Error tras 3 intentos" genérico no le dice si debe corregir algo, esperar o parar.

El modelo no aparece en el reto, y es a propósito. Que un agente sea seguro con acciones reales depende sobre todo de esta capa, que se prueba como cualquier código: con escenarios deterministas y sin modelo.

## Solución explicada paso a paso

:::caution[Contiene spoilers]
Abre estos apartados solo después de intentar el reto. Cada uno explica el fallo, el cambio que aparece en la solución de referencia y la lección que deja.
:::

<details>
<summary>Pedir autorización para acciones destructivas</summary>

**Qué fallaba:** La versión inicial ejecuta todas las operaciones sin llamar a `aprobar`.

**Código original:**

~~~python
# Antes: se entra directamente en el bucle de llamadas.
ultimo: Exception | None = None
for _ in range(REINTENTOS):
    ...
~~~

**Código corregido:**

~~~python
from api_simulada import DESTRUCTIVAS

if accion["operacion"] in DESTRUCTIVAS and not aprobar(accion):
    return f"Acción denegada por la persona de guardia: {accion['operacion']} no se ha hecho."
ultimo: Exception | None = None
~~~

**Cómo se corrige:** La solución importa `DESTRUCTIVAS` y, si la operación es destructiva y `aprobar(accion)` devuelve falso, retorna una denegación sin llamar a la API.

**Qué aprendes:** Los límites de autorización deben implementarse en código; un prompt no constituye un control de permisos.

</details>

<details>
<summary>Evitar duplicados tras un timeout</summary>

**Qué fallaba:** Antes: `api.llamar(accion["operacion"], accion["args"])`. Si la operación se completó pero se perdió la respuesta, un reintento puede ejecutarla dos veces.

**Código original:**

~~~python
return api.llamar(accion["operacion"], accion["args"])
~~~

**Código corregido:**

~~~python
return api.llamar(accion["operacion"], accion["args"],
                  clave=accion["id"])
~~~

**Cómo se corrige:** Después: `api.llamar(accion["operacion"], accion["args"], clave=accion["id"])`. El identificador estable hace idempotentes los reintentos en la API simulada.

**Qué aprendes:** Un timeout no prueba que una acción no se haya realizado. Identificadores estables protegen acciones con efectos secundarios.

</details>

<details>
<summary>No reintentar errores que requieren corregir la petición</summary>

**Qué fallaba:** Antes se reintentaban por igual `Timeout`, `LimiteDeUso` y `Rechazo`.

**Código original:**

~~~python
except (Timeout, LimiteDeUso, Rechazo) as e:
    ultimo = e
~~~

**Código corregido:**

~~~python
except Rechazo as e:
    return f"Error: la API rechaza la petición ({e}). No se ha reintentado."
~~~

**Cómo se corrige:** La solución captura `Rechazo` por separado y devuelve el error sin reintentar.

**Qué aprendes:** Un rechazo de validación no se arregla repitiendo exactamente la misma solicitud.

</details>

<details>
<summary>Respetar la espera cuando hay límites de uso</summary>

**Qué fallaba:** El original vuelve a intentar una llamada incluso si la API pide esperar.

**Código original:**

~~~python
except (Timeout, LimiteDeUso, Rechazo) as e:
    ultimo = e
~~~

**Código corregido:**

~~~python
except LimiteDeUso as e:
    reloj.dormir(e.espera)
    ultimo = e
except Timeout as e:
    ultimo = e
~~~

**Cómo se corrige:** La solución captura `LimiteDeUso` y ejecuta `reloj.dormir(e.espera)` antes de continuar.

**Qué aprendes:** La política de reintentos depende del tipo de error; espera indicada, idempotencia y presupuesto de intentos importan tanto como la propia operación.

</details>

**Comprobación:** ejecuta `uv run python modulos/05-agentes/reto/comprobar.py` sobre tu código. Con `--solucion` se evalúa la implementación de referencia, no tus cambios.

---
title: "Reto del módulo: el diagnóstico del entorno"
description: "Reto del módulo 0, sin solución guiada: arreglar un script que diagnostica el entorno (Ollama, modelos descargados y .env fuera de git) hasta que pase sus criterios de aceptación"
---

:::note[Revisado: 2026-11]
Las salidas son de la máquina del curso, con los modelos de `config/models.toml` de ese momento. La tuya listará los roles y los modelos que tengas configurados.
:::

Las lecciones de este módulo te guían paso a paso. El reto no: tienes un script con fallos, unos criterios de aceptación y un comprobador que te dice cuáles cumples. Cómo llegar es cosa tuya. La solución está en el repositorio, pero ábrela al final, para comparar.

## Objetivos

- Leer el resultado de un comprobador y una excepción para encontrar dónde falla un script que no escribiste tú.
- Distinguir lo que un fichero de configuración dice de lo que de verdad pasa: el nombre de un modelo frente a lo que lista Ollama, y `.gitignore` frente a lo que sigue git.
- Hacer que un diagnóstico falle de forma controlada cuando el servicio que comprueba no está.

## El reto

[`comprobar_entorno.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/comprobar_entorno.py), el de la lección 04, revisa Python, `.env` y los roles sin llamar a nada. Le falta lo que hace falta para trabajar de verdad: que Ollama responde, que los modelos que vas a usar están descargados y que tus claves no han acabado en git.

[`reto/diagnostico.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/reto/diagnostico.py) lo intenta y se equivoca. En la máquina del curso, con todos los modelos descargados, dice esto:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/00-introduccion/reto/diagnostico.py
```

```text
OK    Ollama responde en http://127.0.0.1:11434
OK    rol chat: qwen2.5:1.5b
OK    rol chat_pequeno: qwen2.5:0.5b
OK    rol chat_grande: qwen2.5:7b
OK    rol razonador: qwen3:8b
OK    rol agente: qwen3:8b
OK    rol judge: qwen2.5:7b
FALLA rol embeddings: bge-m3
OK    rol embeddings_otro: qwen3-embedding:0.6b
FALLA rol embeddings_ingles: nomic-embed-text
OK    .env fuera de git
```

Los dos modelos que da por ausentes están descargados. Y no es su único fallo: hay otros dos que en tu máquina, probablemente, no se ven. Arregla el script hasta que cumpla los criterios.

## Criterios de aceptación

1. Con Ollama en marcha, dice que responde.
2. Con Ollama parado, dice que no responde, sin lanzar una excepción.
3. Un modelo con etiqueta (`qwen2.5:1.5b`) que Ollama lista está descargado.
4. Un modelo sin etiqueta en `models.toml` (`bge-m3`) que Ollama lista como `bge-m3:latest` está descargado.
5. Otro tamaño del mismo modelo (`qwen2.5:7b` si solo está `qwen2.5:1.5b`) no cuenta como descargado.
6. Si `.env` está en `.gitignore` pero ya estaba en git, el script dice que está versionado.
7. Si `.env` está en `.gitignore` y fuera de git, dice que no.

No cambies las firmas de las funciones: el comprobador las llama tal como están.

## Cómo se comprueba

[`reto/comprobar.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/reto/comprobar.py) prueba tus funciones con entornos simulados: un Ollama falso, en marcha o parado, y un proyecto temporal con su `.gitignore`. No necesita Ollama ni toca tu repositorio. Con el código de partida:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/00-introduccion/reto/comprobar.py
```

```text
Reto del módulo 0 · reto/diagnostico.py
   OK    con Ollama en marcha, responde
   FALLA con Ollama parado, dice que no responde (sin romperse): lanza ConnectError: conexión rechazada
   OK    un modelo con etiqueta está descargado
   FALLA un modelo sin etiqueta está descargado si Ollama lo lista como :latest: devuelve False, se esperaba True
   OK    otro tamaño del mismo modelo no cuenta como descargado
   FALLA .env en .gitignore, pero ya en git: está versionado: devuelve False, se esperaba True
   OK    .env en .gitignore y fuera de git: no está versionado
4 de 7 criterios. Sigue: lee el primero que falla.
```

El reto está superado cuando dice `Reto superado: 7 de 7 criterios.`. Después, vuelve a ejecutar `diagnostico.py` contra tu entorno real: debería decir lo mismo que antes salvo en los dos modelos.

## Pistas

Ábrelas solo si llevas un rato atascado, y de una en una.

<details>
<summary>Pista 1: el criterio 2</summary>

Cuando no hay nadie escuchando en el puerto, `httpx` no devuelve un código de estado: lanza una excepción. ¿Qué excepción es, y de qué clase base hereda?

</details>

<details>
<summary>Pista 2: el criterio 4</summary>

Ejecuta `ollama list`. ¿Cómo aparece un modelo que descargaste sin etiqueta? ¿Es el mismo modelo que `bge-m3` a secas?

</details>

<details>
<summary>Pista 3: el criterio 6</summary>

`.gitignore` impide que git empiece a seguir un fichero, pero no hace nada con uno que ya sigue. ¿Qué comando de git dice qué ficheros sigue? La función ya recibe un parámetro para eso.

</details>

## La solución

Está en [`reto/solucion/diagnostico.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/reto/solucion/diagnostico.py), con los tres cambios marcados, y se comprueba con `comprobar.py --solucion`. Cada uno es un error que pasa en proyectos reales:

- **Un diagnóstico que se rompe cuando lo que diagnostica falla** no sirve justo cuando hace falta. La comprobación captura `httpx.HTTPError` y responde "no".
- **El nombre de la configuración no es el nombre del servidor.** Ollama completa con `:latest` los modelos sin etiqueta. Comparar cadenas sin normalizarlas da falsos negativos, y en la máquina del curso, dos.
- **Lo que dice un fichero de configuración no es lo que pasa.** `.gitignore` no saca un fichero de git: si `.env` entró antes, sus claves están en el historial aunque hoy esté ignorado. La lección 6.04 explica cómo limpiarlo. Hay que preguntarle a git (`git ls-files .env`), no leer `.gitignore`.

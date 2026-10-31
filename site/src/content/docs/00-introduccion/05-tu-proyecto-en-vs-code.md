---
title: "Tu proyecto en VS Code"
description: "Tu proyecto en VS Code: terminal integrada, tareas, depuración y tests"
---

:::note[Revisado: 2026-10]
Los menús y atajos de VS Code cambian poco, pero cambian. Los atajos son los de Windows y Linux; en macOS, `Ctrl` es `Cmd`.
:::

## Objetivos

Al terminar esta lección podrás:

- Comprobar que VS Code usa el Python del entorno del curso, y corregirlo si no.
- Ejecutar cualquier práctica sin teclear su ruta, con las tareas del curso.
- Depurar una práctica con F5 e inspeccionar la respuesta de un modelo en un punto de ruptura.
- Lanzar los tests desde el panel de pruebas y leer un fallo.

## Teoría

### Por qué VS Code

Las prácticas del curso son scripts de Python que hablan con modelos, leen configuración y registran trazas. Puedes ejecutarlas todas desde la terminal, y las lecciones te dan siempre el comando. Pero en el día a día de un AI Engineer pasas mucho tiempo **dentro** de una llamada al modelo: qué se mandó exactamente, qué volvió, por qué tardó. Para eso, un depurador vale más que cualquier `print`.

Por eso el curso usa VS Code y el repositorio viene preparado para él. En la carpeta `.vscode/` hay cuatro ficheros:

| Fichero | Qué hace |
| --- | --- |
| `extensions.json` | Extensiones recomendadas: Python, su depurador, Ruff y TOML. VS Code ofrece instalarlas al abrir la carpeta |
| `settings.json` | Ruff formatea al guardar, pytest aparece en el panel de pruebas |
| `tasks.json` | Tareas para ejecutar el script abierto, comprobar el entorno, lanzar los tests y pasar el linter |
| `launch.json` | Depuración con F5 del script abierto |

Es la misma idea que el `pom.xml` y la configuración de ejecución compartida de un proyecto Java en equipo: quien clona el repositorio lo tiene todo listo.

### El intérprete: la pieza que lo decide todo

VS Code no sabe por sí solo qué Python usar. Hay dos candidatos: el del sistema, si lo tienes, y el del entorno virtual que creó `uv sync` en `.venv/`. **Solo el de `.venv/` tiene las dependencias del curso.** Si VS Code usa el otro, el editor subraya en rojo librerías que sí están instaladas, y el botón de ejecutar y el depurador fallan.

La terminal no tiene ese problema si usas `uv run`, porque uv siempre usa el entorno del proyecto. Por eso todos los comandos del curso empiezan por `uv run`.

## Práctica

Necesitas haber hecho la lección anterior: uv instalado, `uv sync` ejecutado y Ollama con el modelo descargado.

### 1. Comprueba el intérprete

Abre cualquier fichero `.py`, por ejemplo `modulos/00-introduccion/hola_mundo.py`. Abajo a la derecha, en la barra de estado, VS Code muestra el intérprete activo. Debe indicar `.venv`, con una versión 3.12 o superior.

Si no es así, pulsa `Ctrl+Shift+P`, escribe **Python: Select Interpreter** y elige el que está en `.venv`. Si no aparece en la lista, es que aún no has ejecutado `uv sync`.

### 2. Ejecuta una práctica con una tarea

Con `hola_mundo.py` abierto, pulsa `Ctrl+Shift+P`, escribe **Tasks: Run Task** y elige **Curso: ejecutar el script abierto**. VS Code abre un panel de terminal y ejecuta:

```sh title="Lo que lanza la tarea · raíz del repo"
uv run python "<ruta del fichero abierto>"
```

Es exactamente lo que harías a mano, pero sin teclear la ruta. Las otras tareas del curso son **Curso: comprobar entorno**, **Curso: tests** y **Curso: lint (ruff)**.

### 3. Depura con F5

Ahora vas a ver por dentro una llamada a un modelo.

1. En `hola_mundo.py`, busca la función `preguntar` y haz clic a la izquierda del número de la línea `r.raise_for_status()`. Aparece un punto rojo: es un **punto de ruptura**.
2. Pulsa **F5**. Si VS Code pregunta qué configuración usar, elige **Curso: depurar el script abierto**.
3. El programa se detiene en el punto de ruptura, justo después de recibir la respuesta de Ollama. A la izquierda, en el panel **Variables**, despliega `r`.
4. Abre la **Consola de depuración** (pestaña junto a la terminal) y escribe `r.json()`.

Verás la respuesta completa de Ollama, antes de que el script la recorte. Esta es una real, con el modelo del curso:

```json
{
  "model": "qwen2.5:1.5b",
  "created_at": "2026-10-29T21:45:15.6483812Z",
  "message": {
    "role": "assistant",
    "content": "Un modelo de lenguaje es un programa de computadora diseñado…"
  },
  "done": true,
  "done_reason": "stop",
  "total_duration": 4348618900,
  "load_duration": 3308158200,
  "prompt_eval_count": 45,
  "prompt_eval_cached_count": 0,
  "prompt_eval_duration": 230352000,
  "eval_count": 30,
  "eval_duration": 805510000
}
```

Pulsa **F5** otra vez para que el programa continúe y termine.

### 4. Lanza los tests

Haz clic en el icono del matraz de la barra lateral: es el panel **Testing**. VS Code encuentra los tests del repo con pytest. Pulsa el botón de ejecutar todos. Cada test aparece con un check verde o una cruz roja, y puedes ejecutar o depurar uno solo con los botones que aparecen al pasar el ratón.

También puedes lanzarlos desde la terminal:

```sh title="Terminal de VS Code · raíz del repo"
uv run pytest
```

## Mide y depura

### En qué se van los segundos

La respuesta que viste en el depurador trae mucho más que el texto: Ollama mide cada fase de la llamada, en nanosegundos. Con los datos de arriba:

| Fase | Campo | Tiempo |
| --- | --- | --- |
| Total | `total_duration` | 4,35 s |
| Cargar el modelo en memoria | `load_duration` | 3,31 s |
| Procesar la entrada (45 tokens) | `prompt_eval_duration` | 0,23 s |
| Generar la salida (30 tokens) | `eval_duration` | 0,81 s |

Tres cuartas partes del tiempo se fueron en cargar el modelo: fue la primera llamada después de un rato sin usarlo. Generar costó 0,81 s para 30 tokens, unos 37 tokens por segundo. Con esa tabla ya sabes dónde mirar si una llamada es lenta: si es la carga, mantén el modelo caliente; si es la generación, pide respuestas más cortas o usa un modelo más rápido.

Nada de esto lo habrías visto con el `print` del script. Cuando una llamada se comporte de forma rara, para el programa justo después de recibirla y mira la respuesta entera.

### Depurar dentro de `curso_core`

A partir del módulo 1, las prácticas usan `curso_core`, la librería del curso. Su código está en `packages/curso_core/` y puedes poner puntos de ruptura dentro, igual que en tus scripts. Un buen sitio es el método `_finalizar` de `client.py`: ahí ves cada respuesta ya interpretada, con sus tokens, su latencia y su coste.

## Errores frecuentes

**Pulsar el botón de ejecutar con el intérprete equivocado.** El botón ▷ de VS Code ejecuta el fichero con el intérprete seleccionado, no con `uv run`. Si el seleccionado es el del sistema, falla. Comprueba la barra de estado o usa las tareas del curso, que siempre van por uv.

**Abrir una subcarpeta.** Las tareas y la depuración están en `.vscode/` de la raíz. Si abres `modulos/` o `site/`, no aparecen.

**No ver el entorno tras `uv sync`.** Si `.venv` no sale en **Python: Select Interpreter**, recarga la ventana (`Ctrl+Shift+P` → **Developer: Reload Window**).

### Anatomía de un error: el módulo que no existe (pero sí existe)

Abres `modulos/01-fundamentos-de-llms/prediccion.py`, pulsas el botón ▷ y obtienes:

```text
Traceback (most recent call last):
  File "C:\...\modulos\01-fundamentos-de-llms\prediccion.py", line 13, in <module>
    from curso_core import ClienteLLM, Opciones, TokenGenerado
ModuleNotFoundError: No module named 'curso_core'
```

**Cómo leerlo.** El error está en la línea 13, la del `import`: el programa no ha llegado a hacer nada. `ModuleNotFoundError` significa que el intérprete que lo ejecuta no encuentra ese paquete en su lista de librerías instaladas.

**Causa.** `curso_core` sí está instalado, pero en `.venv/`. El intérprete que ejecutó el script era otro, el Python del sistema, que no lo tiene. Es el error más habitual al empezar con Python en un editor, y siempre es el mismo: el editor y el proyecto no están usando el mismo entorno.

**Solución.** Selecciona el intérprete de `.venv` (paso 1 de la práctica) o ejecuta con la tarea **Curso: ejecutar el script abierto**, que usa `uv run`. Para comprobar qué intérprete se está usando en cada momento, la línea de la barra de estado es tu primera pista.

## Para profundizar

- [Python en VS Code](https://code.visualstudio.com/docs/python/python-tutorial): intérpretes, ejecución y depuración.
- [Depuración en VS Code](https://code.visualstudio.com/docs/debugtest/debugging): puntos de ruptura, panel de variables y consola de depuración.
- [Tareas de VS Code](https://code.visualstudio.com/docs/debugtest/tasks): cómo funcionan las de `.vscode/tasks.json`.
- [Tests de Python en VS Code](https://code.visualstudio.com/docs/python/testing): el panel de pruebas con pytest.
- [Referencia de `/api/chat` de Ollama](https://docs.ollama.com/api/chat): el significado de cada campo de la respuesta.

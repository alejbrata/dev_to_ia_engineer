---
title: "Entorno de trabajo"
description: "Entorno de trabajo: Python, uv, Ollama, claves API, .env, primer \"hola mundo\" con un LLM"
---

:::note[Revisado: 2026-10]
Las instrucciones de instalación cambian con las versiones de las herramientas. Si algo no coincide, manda la documentación oficial enlazada al final.
:::

## Objetivos

Al terminar esta lección podrás:

- Instalar uv y crear el entorno del curso con un solo comando.
- Guardar claves de API en `.env` y explicar por qué los nombres de modelos viven en `config/models.toml`.
- Instalar Ollama, elegir un modelo abierto según tu máquina y descargarlo.
- Hacer tu primera llamada a un LLM desde Python y leer sus tokens y su latencia.

## Teoría

### Python y uv

El curso usa Python 3.12 o superior, gestionado con [uv](https://docs.astral.sh/uv/). uv hace en una sola herramienta lo que antes repartías entre varias: instala versiones de Python, crea entornos virtuales y resuelve e instala dependencias.

Si vienes de Java, piensa en Maven o Gradle con su wrapper:

- `pyproject.toml` es el `pom.xml`: declara el proyecto y sus dependencias.
- `uv.lock` fija la versión exacta de cada dependencia, también de las transitivas. Garantiza que todos instalan lo mismo.
- El **workspace** es un proyecto multimódulo. La raíz agrupa varios paquetes; en este repo, de momento, solo `packages/curso_core`.
- `uv sync` es el equivalente a resolver e instalar. Crea el entorno virtual en `.venv/` y deja todo según el lockfile.
- `uv run <comando>` ejecuta dentro de ese entorno sin tener que activarlo.

Un **entorno virtual** es una carpeta con su propio intérprete y sus propias dependencias, aislada del Python del sistema. Es lo que evita que dos proyectos con versiones distintas de una librería se pisen.

### Dónde se ejecuta todo

Trabajas en VS Code, con tu fork abierto en la raíz (lo preparaste en la lección anterior). Todos los comandos de esta lección van en su terminal integrada, salvo las instalaciones, que valen en cualquier terminal. Cada bloque de comandos lo indica en su título.

Cuando `uv sync` cree el entorno virtual, VS Code lo detectará. En la lección siguiente lo comprobarás y aprenderás a ejecutar y depurar las prácticas desde el editor.

### Claves de API y `.env`

Para llamar a un modelo de pago necesitas una clave de API. Esa clave da acceso a tu cuenta y a tu saldo: trátala como una contraseña.

El curso sigue la regla de la [configuración en el entorno](https://12factor.net/config) de la metodología Twelve-Factor. Los secretos no están en el código; se leen de variables de entorno. Para no tener que exportarlas a mano, se guardan en un fichero `.env` en la raíz del repo, que el código carga al arrancar.

Hay dos ficheros:

- `.env.example` se versiona. Lista las variables que el curso usa, todas vacías. Sirve de plantilla.
- `.env` no se versiona: está en `.gitignore`. Es tu copia con los valores reales.

Es el mismo patrón que externalizar las credenciales de un `application.properties` en un backend Java.

### Los modelos en `config/models.toml`

Los nombres de modelos cambian cada pocos meses. Si estuvieran repartidos por el código, cada cambio obligaría a tocar muchos ficheros.

Por eso el curso los centraliza en `config/models.toml`, organizados por **rol**: `chat` para generación general, `judge` para evaluar respuestas y `embeddings` para búsqueda semántica. El código pide "el modelo de chat", no un nombre concreto. Cambiar de modelo, o de proveedor, es editar una línea.

### Modelos en local con Ollama

Para la primera llamada no vas a usar un proveedor de pago. Vas a ejecutar el modelo en tu máquina. Es más trabajo que pegar una clave de API, pero a cambio ves todas las piezas: de dónde sale el modelo, cuánto ocupa, cuánta memoria necesita y qué tarda en responder. Y no cuesta dinero.

[Ollama](https://ollama.com) es un servidor que descarga modelos abiertos, los carga en memoria y los expone con una API HTTP en `http://localhost:11434`. Para tu código es un servicio más al que hablar por HTTP, como una base de datos que levantas en local para desarrollar.

### Cómo elegir un modelo

Un modelo abierto se describe con tres datos que verás en todas partes:

- **Tamaño en parámetros.** Los pesos que ha aprendido el modelo, expresados en miles de millones: `1.7b`, `8b`, `70b`. Más parámetros suele significar respuestas mejores, y siempre significa más memoria y más lentitud.
- **Cuantización.** Cuántos bits se usan para guardar cada peso. Un modelo cuantizado a 4 bits (`q4`) ocupa aproximadamente una cuarta parte que en 16 bits (`fp16`), a cambio de perder algo de calidad. Lo verás a fondo en el módulo 7.
- **Licencia.** Qué puedes hacer con el modelo. Algunas son abiertas de verdad (Apache 2.0, MIT) y otras imponen condiciones de uso. Léela antes de usar un modelo en un producto.

La regla práctica: el modelo tiene que caber en tu memoria con margen. Lo que ocupa la descarga es una buena primera estimación de lo que ocupará en RAM (o en la memoria de la GPU, si tienes), más algo extra para el contexto. La [documentación de Ollama](https://github.com/ollama/ollama) recomienda al menos 8 GB de RAM para modelos de unos 7 mil millones de parámetros.

Para este curso, el modelo de chat por defecto es pequeño a propósito. Funciona en casi cualquier portátil, sin GPU, y responde lo bastante bien para aprender. No esperes de él la calidad de un modelo comercial grande; esa diferencia también es algo que aprenderás a medir.

Puedes usar el modelo que quieras o que tu máquina aguante. El curso no depende de ninguno: el código lee el nombre de `config/models.toml`, y cambiarlo es editar una línea.

:::note[Revisado: 2026-10]
El curso se ha construido y probado con **Qwen2.5 1.5B Instruct** (`qwen2.5:1.5b` en Ollama), que es el que viene configurado. Es del equipo Qwen de Alibaba, tiene licencia Apache 2.0 y está en la biblioteca de Ollama y en el Hub de Hugging Face. La descarga ocupa unos 1 GB y, cargado, usa unos 1,2 GB de memoria. Es multilingüe y responde en español, algo que no todos los modelos pequeños hacen (lo verás en "Errores frecuentes").

Las salidas y métricas de esta lección son de ese modelo. Con otro, los números y las respuestas cambiarán.
:::

### De dónde salen los modelos

Hay dos sitios principales:

- **La [biblioteca de Ollama](https://ollama.com/library).** Modelos ya empaquetados. Cada uno tiene etiquetas (tags) que indican tamaño y cuantización, como `modelo:1.5b` o `modelo:1.5b-instruct-q4_K_M`.
- **El [Hub de Hugging Face](https://huggingface.co/models).** El gran repositorio de modelos abiertos. Cada modelo tiene una ficha (model card) con su licencia, sus idiomas y cómo se entrenó. Ollama puede ejecutar directamente cualquier modelo del Hub en formato GGUF con `ollama run hf.co/{usuario}/{repositorio}:{cuantización}`. Lo verás en el anexo de Hugging Face.

Antes de elegir un modelo, lee su ficha. Fíjate en tres cosas: la licencia, los idiomas con los que se entrenó y que sea la variante **instruct** (o **chat**). Esa es la versión ajustada para seguir instrucciones y conversar. La versión base solo continúa texto y no responde a preguntas como esperas.

## Práctica

### 1. Instala uv

En macOS o Linux:

```sh title="Cualquier terminal"
curl -LsSf https://astral.sh/uv/install.sh | sh
```

En Windows (PowerShell):

```powershell title="Cualquier terminal · PowerShell"
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

También puedes usar `brew install uv` o `winget install --id=astral-sh.uv -e`.

Después de instalarlo, **cierra la terminal de VS Code y abre una nueva** (o reinicia VS Code). Una terminal que ya estaba abierta no ve los programas recién instalados. Comprueba la instalación:

```sh title="Terminal de VS Code"
uv --version
```

No hace falta que instales Python aparte. Si no tienes una versión compatible, uv la descarga.

### 2. Crea el entorno

Desde la raíz del repo:

```sh title="Terminal de VS Code · raíz del repo"
uv sync
```

### 3. Crea tu `.env`

Copia la plantilla.

En macOS o Linux:

```sh title="Terminal de VS Code · raíz del repo"
cp .env.example .env
```

En Windows (PowerShell):

```powershell title="Terminal de VS Code · raíz del repo · PowerShell"
Copy-Item .env.example .env
```

De momento, déjalo vacío. Las claves se rellenan cuando una práctica las necesite.

### 4. Instala Ollama

Descarga el instalador desde [ollama.com/download](https://ollama.com/download) o usa la terminal.

En macOS o Linux:

```sh title="Cualquier terminal"
curl -fsSL https://ollama.com/install.sh | sh
```

En Windows (PowerShell):

```powershell title="Cualquier terminal · PowerShell"
irm https://ollama.com/install.ps1 | iex
```

En macOS y Windows, Ollama se queda arrancado en segundo plano. En Linux, si no arranca solo, lánzalo con `ollama serve`. Comprueba que responde:

```sh title="Cualquier terminal"
ollama --version
curl http://localhost:11434/api/version
```

La segunda orden debe devolver un JSON con la versión. Si no responde, el servidor no está arrancado.

### 5. Descarga el modelo

Descarga el modelo con el que se ha construido el curso:

```sh title="Cualquier terminal"
ollama pull qwen2.5:1.5b
```

Si prefieres otro, descárgalo con su nombre y cámbialo en `config/models.toml`:

```toml
[roles.chat]
provider = "ollama"
model = "el-modelo-que-elijas"
```

Sea cual sea, pruébalo desde la terminal antes de usarlo desde Python:

```sh title="Cualquier terminal"
ollama run qwen2.5:1.5b "Hola, ¿en qué idioma me respondes?"
```

Otras órdenes que vas a usar:

```sh title="Cualquier terminal"
ollama list    # modelos descargados y lo que ocupan en disco
ollama ps      # modelos cargados en memoria ahora mismo
ollama rm <modelo>   # borra un modelo descargado
```

### 6. Comprueba el entorno

El script [`comprobar_entorno.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/comprobar_entorno.py) revisa tu configuración sin llamar a ningún modelo ni mostrar el valor de las claves:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/00-introduccion/comprobar_entorno.py
```

Con el `.env` recién copiado verás esto:

```text
Python
  OK versión 3.13 (mínimo 3.12)
  OK entorno virtual: /ruta/al/repo/.venv/bin/python

Variables (.env)
  OK encontrado /ruta/al/repo/.env
  -- ANTHROPIC_API_KEY
  -- OPENAI_API_KEY
  ...

Modelos (config/models.toml)
  OK chat
  OK chat_compatible
  OK remoto
  -- judge
  -- embeddings

Todo listo.
```

`OK` indica que algo está configurado y `--` que no lo está. Las claves y los roles vacíos no son un problema todavía; solo cuentan como error un Python antiguo o la falta de `.env`. Los roles `chat_compatible` y `remoto` los usarás en el módulo 1.

### 7. Tu primer "hola mundo" con un LLM

El script [`hola_mundo.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/hola_mundo.py) lee el modelo de `config/models.toml`, le hace una pregunta por la API HTTP de Ollama e imprime la respuesta con sus métricas:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/00-introduccion/hola_mundo.py
```

```text
> Explica en una sola frase qué es un modelo de lenguaje.

Un modelo de lenguaje es un sistema artificial que aprende a entender y generar el lenguaje humano, similar a cómo los seres humanos comunicamos y comprenderán el mundo.

[qwen2.5:1.5b] tokens entrada=44 salida=41 · latencia=4.83s (carga del modelo 1.55s)
```

Tu respuesta será distinta: el modelo no devuelve siempre lo mismo. Fíjate en la frase final: "comprenderán" no concuerda. Un modelo de este tamaño comete errores así, y es bueno verlos desde el primer día.

Puedes pasarle tu propia pregunta:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/00-introduccion/hola_mundo.py "¿Qué es un token?"
```

Lee el código. Son menos de 100 líneas sin magia: un `POST` a `/api/chat` con `httpx`, la respuesta validada con un modelo de Pydantic y un cronómetro alrededor de la llamada. No usa ningún SDK de proveedor: es HTTP, como cualquier otra API que hayas integrado.

## Mide y depura

### Las métricas del "hola mundo"

La última línea del script tiene las primeras métricas del curso. Ejecútalo dos veces seguidas y compara. Estos son los datos reales de dos ejecuciones en un equipo sin GPU (`ollama ps` mostraba `100% CPU`):

| | Tokens de entrada | Tokens de salida | Latencia | Carga del modelo |
| --- | --- | --- | --- | --- |
| Primera llamada | 44 | 41 | 4,83 s | 1,55 s |
| Segunda llamada | 44 | 47 | 3,30 s | 0,00 s |

La primera llamada es más lenta porque Ollama tiene que cargar el modelo en memoria. Es un **arranque en frío**, como la primera petición a un servidor de aplicaciones que aún no ha calentado. Ollama mantiene el modelo cargado unos minutos; después lo descarga y la siguiente llamada vuelve a pagar la carga. Con `ollama ps` ves qué hay cargado y hasta cuándo.

Ahora pregunta "¿Qué es un token?". En la misma máquina, la respuesta tuvo 425 tokens de salida y tardó 14,02 s. La latencia depende sobre todo de cuántos tokens genera el modelo, no de cuántos le mandas. Es la primera intuición de coste y rendimiento que tienes que fijar: **controla la longitud de la salida**.

### Diagnosticar el entorno

Cuando algo no funciona en Python, la primera pregunta es casi siempre la misma: ¿qué intérprete se está ejecutando? Compruébalo:

```sh title="Terminal de VS Code · raíz del repo"
uv run python -c "import sys; print(sys.executable)"
```

Debe apuntar a `.venv` dentro del repo. Otras órdenes útiles:

```sh title="Terminal de VS Code · raíz del repo"
uv python list    # versiones de Python disponibles e instaladas
uv tree           # árbol de dependencias del proyecto
```

Los dos scripts terminan con código de salida 0 si todo va bien y 1 si no. Ese código lo puedes usar en scripts y en CI:

```sh title="Terminal de VS Code · raíz del repo"
echo $?            # macOS / Linux
echo $LASTEXITCODE # Windows (PowerShell)
```

## Errores frecuentes

**Ejecutar con el Python del sistema.** Si lanzas `python script.py` en lugar de `uv run python script.py`, se usa el intérprete global, que no tiene las dependencias del proyecto. El síntoma típico es `ModuleNotFoundError: No module named '...'` con una librería que sí está en `pyproject.toml`. Usa siempre `uv run`.

**Ollama no está arrancado.** El script lo detecta y te lo dice:

```text
No hay nadie escuchando en http://localhost:11434. ¿Está Ollama arrancado?
```

Arranca la aplicación o ejecuta `ollama serve`. Ten en cuenta que Ollama se actualiza solo: durante la actualización el servidor se para y las órdenes fallan con `Error: upgrade in progress...`. Espera a que termine.

**La descarga se corta.** Con conexiones inestables, `ollama pull` puede fallar a mitad con `Error: unexpected EOF`. Vuelve a lanzarlo: continúa desde donde lo dejó.

**El modelo responde en otro idioma.** Muchos modelos pequeños se entrenan casi solo con texto en inglés. Esto es lo que respondió uno de ellos a la pregunta del script:

```text
> Explica en una sola frase qué es un modelo de lenguaje.

A language model, also known as a chatbot or a virtual assistant, is a computational model that uses artificial intelligence and natural language processing to generate human-like responses to user inquiries.
```

No es un fallo del código: es una limitación del modelo, y estaba en su ficha. Antes de elegir un modelo, comprueba los idiomas que soporta.

**La respuesta no es la que esperabas.** Al preguntar "¿Qué es un token?", el modelo habló de tokens de autenticación (JWT, sesiones), no de tokens de un LLM. No se equivocó: la pregunta era ambigua y no le diste contexto. Es el primer aviso de algo que verás en todo el curso: el modelo solo sabe lo que hay en su entrenamiento y en lo que le mandas.

**Subir `.env` al repositorio.** Antes de cada commit, mira `git status`: `.env` no debe aparecer. Si alguna vez subes una clave, no basta con borrar el fichero en otro commit: la clave sigue en el historial. Revócala en el panel del proveedor y genera otra. Cómo limpiar el historial se ve en el módulo 6.

### Anatomía de un error: el 404 que no dice por qué

Escribes mal el nombre del modelo en `config/models.toml` (por ejemplo, `qwen2.5:1.5` en lugar de `qwen2.5:1.5b`) y llamas a la API sin capturar la excepción:

```text
Traceback (most recent call last):
  ...
  File ".../modulos/00-introduccion/hola_mundo.py", line 65, in preguntar
    r.raise_for_status()
  File ".../httpx/_models.py", line 829, in raise_for_status
    raise HTTPStatusError(message, request=request, response=self)
httpx.HTTPStatusError: Client error '404 Not Found' for url 'http://localhost:11434/api/chat'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404
```

**Cómo leerlo.** Lee de abajo arriba. La última línea dice que el servidor devolvió un 404 a `POST /api/chat`. La línea anterior en tu código es `raise_for_status()`, que convierte cualquier código 4xx o 5xx en excepción. Hasta aquí sabes qué falló, pero no por qué: la ruta `/api/chat` existe, así que el 404 no es de URL.

**Causa.** El motivo está en el cuerpo de la respuesta, que la excepción no muestra:

```json
{"error":"model 'qwen2.5:1.5' not found"}
```

Ollama devuelve 404 cuando el modelo pedido no está descargado. Aquí, porque el nombre está mal escrito.

**Solución.** Corrige el nombre o descarga el modelo con `ollama pull`. Y, sobre todo, cuando captures errores HTTP, registra siempre el cuerpo de la respuesta. Es lo que hace `hola_mundo.py`:

```python
except httpx.HTTPStatusError as e:
    print(f"Ollama respondió {e.response.status_code}: {e.response.text}")
```

Es la misma lección que en cualquier integración backend: el código de estado dice qué categoría de error es; el cuerpo dice qué ha pasado.

## Bitácora

TODO(alex)

## Para profundizar

- [Instalación de uv](https://docs.astral.sh/uv/getting-started/installation/) y [workspaces de uv](https://docs.astral.sh/uv/concepts/projects/workspaces/).
- [The Twelve-Factor App: Config](https://12factor.net/config). Por qué la configuración va en el entorno.
- [Documentación de Ollama](https://docs.ollama.com/): [referencia de `/api/chat`](https://docs.ollama.com/api/chat) y [preguntas frecuentes](https://docs.ollama.com/faq).
- [Usar Ollama con modelos GGUF del Hub de Hugging Face](https://huggingface.co/docs/hub/ollama).
- [Ficha de Qwen2.5 1.5B Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) en Hugging Face.
- [python-dotenv](https://github.com/theskumar/python-dotenv) y [`tomllib`](https://docs.python.org/3/library/tomllib.html).
- [Python en VS Code](https://code.visualstudio.com/docs/python/python-tutorial) y [documentación de Ruff](https://docs.astral.sh/ruff/).

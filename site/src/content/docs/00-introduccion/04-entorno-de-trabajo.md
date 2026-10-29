---
title: "Entorno de trabajo"
description: "Entorno de trabajo: Python, uv, VS Code, claves API, .env, primer \"hola mundo\" con un LLM"
---

:::note[Revisado: 2026-10]
Las instrucciones de instalación cambian con las versiones de las herramientas. Si algo no coincide, manda la documentación oficial enlazada al final.
:::

## Objetivos

Al terminar esta lección podrás:

- Instalar uv y crear el entorno del curso con un solo comando.
- Configurar VS Code para que use el entorno virtual del repo.
- Guardar claves de API en `.env` sin riesgo de subirlas al repositorio.
- Explicar por qué los nombres de modelos viven en `config/models.toml` y no en el código.
- Ejecutar el script de comprobación del entorno e interpretar su salida.

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

### VS Code

Puedes usar cualquier editor. Si usas VS Code, instala dos extensiones: **Python** (de Microsoft) y **Ruff** (de Astral). La primera da autocompletado y depuración; la segunda marca los errores de lint y formatea al guardar.

Lo importante es que el editor use el intérprete de `.venv/`. Si no, marcará como inexistentes librerías que sí están instaladas.

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

### El primer "hola mundo" con un LLM

TODO: pendiente de decidir el proveedor de la primera llamada.

## Práctica

### 1. Instala uv

En macOS o Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

En Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

También puedes usar `brew install uv` o `winget install --id=astral-sh.uv -e`. Comprueba la instalación con `uv --version`.

No hace falta que instales Python aparte. Si no tienes una versión compatible, uv la descarga.

### 2. Crea el entorno

Desde la raíz del repo:

```sh
uv sync
```

### 3. Crea tu `.env`

Copia la plantilla.

En macOS o Linux:

```sh
cp .env.example .env
```

En Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

De momento, déjalo vacío. Las claves se rellenan cuando una práctica las necesite.

### 4. Configura VS Code

Abre la carpeta del repo, pulsa `Ctrl+Shift+P` (`Cmd+Shift+P` en macOS) y elige **Python: Select Interpreter**. Selecciona el que está en `.venv`.

### 5. Comprueba el entorno

El script [`comprobar_entorno.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/00-introduccion/comprobar_entorno.py) revisa tu configuración sin llamar a ningún proveedor ni mostrar el valor de las claves:

```sh
uv run python modulos/00-introduccion/comprobar_entorno.py
```

Con el `.env` recién copiado, verás algo así:

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
  -- chat
  -- judge
  -- embeddings

Todo listo.
```

`OK` indica que algo está configurado y `--` que no lo está. Las variables y los roles vacíos no son un problema todavía; solo cuentan como error un Python antiguo o la falta de `.env`.

Lee el código del script. Es corto y usa `python-dotenv` para leer `.env` y `tomllib`, de la librería estándar, para leer `models.toml`.

## Mide y depura

Cuando algo no funciona en Python, la primera pregunta es casi siempre la misma: ¿qué intérprete se está ejecutando? Compruébalo:

```sh
uv run python -c "import sys; print(sys.executable)"
```

Debe apuntar a `.venv` dentro del repo. Otras órdenes útiles para diagnosticar:

```sh
uv python list    # versiones de Python disponibles e instaladas
uv tree           # árbol de dependencias del proyecto
```

El script de comprobación termina con código de salida 0 si todo está bien y 1 si no. Ese código lo puedes usar en scripts y en CI. Para verlo después de ejecutarlo:

```sh
echo $?            # macOS / Linux
echo $LASTEXITCODE # Windows (PowerShell)
```

## Errores frecuentes

**Ejecutar con el Python del sistema.** Si lanzas `python script.py` en lugar de `uv run python script.py`, se usa el intérprete global, que no tiene las dependencias del proyecto. El síntoma típico es `ModuleNotFoundError: No module named '...'` con una librería que sí está en `pyproject.toml`. Usa siempre `uv run`.

**Subir `.env` al repositorio.** Antes de cada commit, mira `git status`: `.env` no debe aparecer. Si alguna vez subes una clave, no basta con borrar el fichero en otro commit: la clave sigue en el historial. Revócala en el panel del proveedor y genera otra. Cómo limpiar el historial se ve en el módulo 6.

**Imprimir claves para depurar.** Un `print(os.environ)` acaba en logs, capturas de pantalla o issues públicos. Para comprobar una clave, mira si existe, nunca su valor.

### Anatomía de un error: un valor TOML sin comillas

Editas `config/models.toml` para configurar tu modelo de chat y escribes:

```toml
[roles.chat]
provider = ""
model = mi-modelo
```

Al ejecutar el script de comprobación:

```text
Traceback (most recent call last):
  File ".../modulos/00-introduccion/comprobar_entorno.py", line 83, in <module>
    sys.exit(main())
  File ".../modulos/00-introduccion/comprobar_entorno.py", line 75, in main
    for rol, ok in roles_configurados(leer_modelos(RAIZ / "config" / "models.toml")).items():
  File ".../modulos/00-introduccion/comprobar_entorno.py", line 35, in leer_modelos
    return tomllib.load(f)
  File ".../tomllib/_parser.py", line 66, in load
  ...
tomllib.TOMLDecodeError: Invalid value (at line 18, column 9)
```

**Cómo leerlo.** Lee el traceback de abajo arriba. La última línea dice qué pasó: un valor no válido en la línea 18, columna 9. Las líneas anteriores dicen dónde: dentro de `tomllib`, llamado desde `leer_modelos`. Las que están dentro de `tomllib` no te interesan; el problema no está en la librería estándar, sino en lo que le pasas.

**Causa.** En la línea 18, columna 9, empieza `mi-modelo`. En TOML, los textos van entre comillas. Sin ellas, el parser no sabe qué tipo de valor es.

**Solución.** `model = "mi-modelo"`. El patrón general: cuando un error señala una posición en un fichero de configuración, ve a esa línea y columna antes de mirar el código.

## Bitácora

TODO(alex)

## Para profundizar

- [Instalación de uv](https://docs.astral.sh/uv/getting-started/installation/) y [workspaces de uv](https://docs.astral.sh/uv/concepts/projects/workspaces/).
- [The Twelve-Factor App: Config](https://12factor.net/config). Por qué la configuración va en el entorno.
- [python-dotenv](https://github.com/theskumar/python-dotenv): la librería que carga `.env`.
- [`tomllib`](https://docs.python.org/3/library/tomllib.html) en la documentación de Python.
- [Python en VS Code](https://code.visualstudio.com/docs/python/python-tutorial).
- [Documentación de Ruff](https://docs.astral.sh/ruff/).

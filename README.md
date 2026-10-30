# Curso de AI Engineer (sin humo)

Curso abierto, en español, para formarse como AI Engineer: construir, medir, depurar y poner en producción sistemas basados en LLMs. Pensado para desarrolladores con experiencia, sobre todo backend, sin experiencia previa en ML.

El temario y su estado están en [`docs/PLAN.md`](docs/PLAN.md).

Para leerlo, entra en la web: **https://alejbrata.github.io/dev_to_ia_engineer/**. Para hacer las prácticas, sigue estos pasos.

## Empieza aquí

### 1. Requisitos

| Qué | Para qué | Dónde |
| --- | --- | --- |
| git y una cuenta de GitHub | Tener tu copia del curso | [git-scm.com](https://git-scm.com/downloads) |
| VS Code | El editor del curso: el repo trae tareas, depuración y extensiones | [code.visualstudio.com](https://code.visualstudio.com/) |
| uv | Python 3.12+ y las dependencias (instala Python si no lo tienes) | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| Ollama | Ejecutar los modelos en local, gratis | [ollama.com/download](https://ollama.com/download) |

Un portátil con 8 GB de RAM y sin GPU basta para el modelo del curso. No hace falta ninguna clave de API de pago.

### 2. Tu copia del repositorio

Haz un **fork** en GitHub, clónalo y abre la carpeta raíz en VS Code. Acepta las extensiones recomendadas que te ofrece.

```sh
git clone https://github.com/TU_USUARIO/dev_to_ia_engineer.git
code dev_to_ia_engineer
```

### 3. Instala y comprueba (en la terminal de VS Code, desde la raíz)

```sh
uv sync                        # crea .venv con Python y todas las dependencias
cp .env.example .env           # Windows (PowerShell): Copy-Item .env.example .env
ollama pull qwen2.5:1.5b       # el modelo del curso, ~1 GB
uv run python modulos/00-introduccion/comprobar_entorno.py
uv run pytest                  # los tests deben pasar
```

Si todo va bien, el script de comprobación termina con `Todo listo.`. A partir de aquí, cada lección indica qué ejecutar. También puedes lanzar cualquier práctica con la tarea de VS Code **Curso: ejecutar el script abierto** o depurarla con **F5**.

### Sin uv: con pip

El curso usa uv, pero también funciona con el `pip` de siempre y Python 3.12 o superior. `requirements.txt` se genera desde el mismo lockfile (`uv export`), así que instala exactamente las mismas versiones:

```sh
python -m venv .venv
# Activa el entorno. Windows: .venv\Scripts\activate · macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python modulos/00-introduccion/comprobar_entorno.py
```

En las lecciones, sustituye `uv run python` por `python` con el entorno activado.

### Opcional, para algunas lecciones

- `ollama pull qwen2.5:0.5b` y `ollama pull qwen2.5:7b`: comparar tamaños de modelo (lección 05 del módulo 1, ~5 GB).
- [llama.cpp](https://github.com/ggml-org/llama.cpp): comparar cómo tratan dos servidores un prompt demasiado largo (lección 02 del módulo 1) y servir el reranker (lección 05 del módulo 3, ~0,6 GB).
- `ollama pull nomic-embed-text` y `ollama pull qwen3-embedding:0.6b`: comparar modelos de embeddings (lección 03 del módulo 3, ~1 GB).
- Docker con Compose y `docker compose up -d`: el índice vectorial en PostgreSQL con pgvector (lección 03 del módulo 3).
- `HF_TOKEN` en `.env`: ver los errores reales de un proveedor en la nube (lección 04 del módulo 1). Sin créditos en Hugging Face solo verás errores; la práctica lo explica.

## Estructura

| Ruta | Contenido |
| --- | --- |
| `site/` | Web del curso (Astro + Starlight) |
| `packages/curso_core/` | Librería compartida: cliente LLM, tracing y métricas |
| `modulos/NN-*/` | Código de las prácticas de cada módulo |
| `prompts/` | Prompts versionados en Markdown, reutilizables |
| `config/models.toml` | Nombres de los modelos que usa el curso |
| `bitacora/` | Experiencia personal del autor, módulo a módulo |
| `.vscode/` | Configuración de VS Code: extensiones, tareas y depuración |
| `scripts/` | Utilidades del repo (sidebar desde el plan, medidas de la web) |
| `requirements.txt` | Dependencias para pip, generadas desde `uv.lock` |

## Arrancar la web en local

Solo hace falta para contribuir al curso. Requiere Node.js 22.23.4 o superior.

```sh
cd site
npm install
npm run dev
```

## Licencias

El repositorio tiene dos licencias:

- **Contenido** (texto de las lecciones en `site/src/content/`, `bitacora/` y `docs/`): [CC BY-SA 4.0](LICENSE-CONTENT). Puedes copiarlo y adaptarlo, también con fines comerciales, si citas la fuente y publicas tus cambios con la misma licencia.
- **Código** (`packages/`, `modulos/`, `scripts/`, `tests/` y la configuración de `site/`): [MIT](LICENSE). Puedes usarlo en tus proyectos, incluso cerrados, conservando el aviso de copyright.

Los fragmentos de código incluidos dentro de las lecciones también se pueden usar bajo MIT.

## Contribuir

Lee [`CONTRIBUTING.md`](CONTRIBUTING.md).

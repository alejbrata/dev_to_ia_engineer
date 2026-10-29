# Curso de AI Engineer (sin humo)

Curso abierto, en español, para formarse como AI Engineer: construir, medir, depurar y poner en producción sistemas basados en LLMs. Pensado para desarrolladores con experiencia, sobre todo backend, sin experiencia previa en ML.

El temario y su estado están en [`docs/PLAN.md`](docs/PLAN.md).

## Estructura

| Ruta | Contenido |
| --- | --- |
| `site/` | Web del curso (Astro + Starlight) |
| `packages/curso_core/` | Librería compartida: cliente LLM, tracing y métricas |
| `modulos/NN-*/` | Código de las prácticas de cada módulo |
| `bitacora/` | Experiencia personal del autor, módulo a módulo |
| `config/models.toml` | Nombres de los modelos que usa el curso |
| `scripts/plan_sync.py` | Genera el sidebar y el esqueleto de lecciones desde el plan |

## Arrancar la web

Requiere Node.js 22.23.4 o superior.

```sh
cd site
npm install
npm run dev
```

## Arrancar el código

Haz un fork del repositorio, clónalo y ábrelo en [VS Code](https://code.visualstudio.com/): viene configurado con extensiones recomendadas, tareas y depuración (carpeta `.vscode/`). Necesitas [uv](https://docs.astral.sh/uv/), que instala Python 3.12+ si no lo tienes, y [Ollama](https://ollama.com) para ejecutar modelos en local. Las lecciones 03, 04 y 05 del módulo 0 lo explican paso a paso.

```sh
uv sync
cp .env.example .env   # y rellena las claves que vayas a usar
uv run ruff check
uv run pytest
```

## Licencias

El repositorio tiene dos licencias:

- **Contenido** (texto de las lecciones en `site/src/content/`, `bitacora/` y `docs/`): [CC BY-SA 4.0](LICENSE-CONTENT). Puedes copiarlo y adaptarlo, también con fines comerciales, si citas la fuente y publicas tus cambios con la misma licencia.
- **Código** (`packages/`, `modulos/`, `scripts/`, `tests/` y la configuración de `site/`): [MIT](LICENSE). Puedes usarlo en tus proyectos, incluso cerrados, conservando el aviso de copyright.

Los fragmentos de código incluidos dentro de las lecciones también se pueden usar bajo MIT.

## Contribuir

Lee [`CONTRIBUTING.md`](CONTRIBUTING.md).

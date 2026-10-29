# site

Web del curso (Astro + Starlight).

```sh
npm install
npm run dev      # servidor local
npm run build    # build de producción en dist/
```

Las páginas viven en `src/content/docs/`. El sidebar (`src/sidebar.json`) y el esqueleto de las lecciones se generan desde `docs/PLAN.md` con `uv run python scripts/plan_sync.py`, desde la raíz del repo.

## Componentes interactivos y medidas reales

La portada y algunas lecciones usan componentes propios en `src/components/` (consola de la portada, visor de tokens, deslizador de temperatura, repetición del streaming). Los datos que muestran salen de `src/data/medidas.json`, grabado con llamadas reales al modelo del curso. Para regenerarlo, con Ollama arrancado y desde la raíz del repo:

```sh
uv run python scripts/datos_web.py
```

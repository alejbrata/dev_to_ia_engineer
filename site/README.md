# site

Web del curso (Astro + Starlight).

```sh
npm install
npm run dev      # servidor local
npm run build    # build de producción en dist/
```

Las páginas viven en `src/content/docs/`. El sidebar (`src/sidebar.json`) y el esqueleto de las lecciones se generan desde `docs/PLAN.md` con `uv run python scripts/plan_sync.py`, desde la raíz del repo.

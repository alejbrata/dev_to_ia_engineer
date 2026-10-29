# Cómo contribuir

Gracias por querer mejorar el curso. Las contribuciones se aceptan por pull request.

## Proponer cambios

1. Para erratas y arreglos pequeños, abre un PR directamente.
2. Para cambios grandes (una lección nueva, reorganizar un módulo), abre antes un issue para hablarlo.
3. Haz cambios pequeños: un PR, un tema.
4. Antes de abrir el PR, comprueba que todo pasa:

   ```sh
   cd site && npm run build
   uv run ruff check && uv run ruff format --check
   uv run pytest
   ```

5. Usa [Conventional Commits](https://www.conventionalcommits.org/es/) en los mensajes (`feat:`, `fix:`, `docs:`…).

## Temario

`docs/PLAN.md` es la fuente de verdad del temario. Si añades, quitas o renombras una lección, edita el plan y ejecuta:

```sh
uv run python scripts/plan_sync.py
```

El script regenera el sidebar y crea el esqueleto de las lecciones nuevas. No borra ni sobrescribe páginas: si renombras una, mueve tú el fichero. Un test comprueba que la web y el plan coinciden.

## Enlaces internos

La web se publica en GitHub Pages bajo la subruta `/dev_to_ia_engineer/`. En los enlaces internos de las lecciones usa rutas relativas (`../02-que-hace-un-ai-engineer/`) o incluye la subruta (`/dev_to_ia_engineer/03-rag/01-cuando-usar-rag/`).

## Estilo

- Español de España, con tuteo y tono directo y técnico. Frases cortas.
- Términos técnicos en inglés cuando es lo habitual (embedding, chunking, tracing), explicados la primera vez.
- Sin humo: nada de "revolucionario" ni "potente". Si algo tiene limitaciones, se dice.
- Cada lección sigue las secciones: Objetivos, Teoría, Práctica, Mide y depura, Errores frecuentes, Bitácora y Para profundizar.
- Código en Python 3.12+, con type hints, que pase ruff y pytest.
- Los nombres de modelos van solo en `config/models.toml`. Los secretos, solo en `.env`.
- No copies material con copyright: explica con tus palabras y enlaza la fuente.

## La bitácora

La sección **Bitácora** de cada lección cuenta la experiencia personal del autor y sale **solo** de los ficheros `bitacora/NN-*.md`, que escribe directamente el autor.

- No se aceptan cambios que añadan o inventen experiencias, anécdotas u opiniones del autor.
- Sí se aceptan correcciones de erratas y estilo que no cambien los hechos.

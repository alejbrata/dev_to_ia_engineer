# Módulo 8 — Proyecto final: código de las prácticas

- `plantilla/`: el esqueleto de un proyecto. Cópiala a `proyectos/<tu-proyecto>/` en tu fork: manifiesto (`proyecto.toml`), `app.py` con `curso_core`, su prompt, `evaluar.py` (resultados con tokens, latencia y coste), un test y el README con las seis secciones (lección 01).
- `comprobar_proyecto.py`: comprueba los requisitos mínimos a partir del manifiesto, mirando lo que contiene cada fichero (lección 02).
- `rubrica.toml` y `rubrica.py`: la rúbrica, y el contraste de tu `autoevaluacion.toml` con la evidencia (lección 03).
- `ejemplo/`: el ejemplo resuelto, el asistente del curso descrito como proyecto final: manifiesto, autoevaluación y README de portafolio (lecciones 02 a 04).
- `test_comprobar_proyecto.py` y `test_rubrica.py`: sin red ni modelos.

```sh
uv run python modulos/08-proyecto-final/comprobar_proyecto.py modulos/08-proyecto-final/ejemplo/proyecto.toml [--tests]
uv run python modulos/08-proyecto-final/rubrica.py modulos/08-proyecto-final/ejemplo/proyecto.toml
```

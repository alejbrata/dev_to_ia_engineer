# CLAUDE.md — Curso de AI Engineer (sin humo)

Este fichero te da el contexto que no tienes. Léelo entero antes de cualquier tarea.

## Qué es este proyecto

Un curso abierto, en español, para formarse como **AI Engineer**: alguien que construye, mide, depura y pone en producción sistemas basados en LLMs. No es un curso de "prompts mágicos" ni de hype. El objetivo es que quien lo termine pueda trabajar en el puesto.

Se publica como web (Astro + Starlight) y el repo está abierto a contribuciones.

## Autor

Alex, Senior Systems Engineer con más de 10 años en backend Java enterprise (administración pública, WebSphere, frameworks corporativos). Hizo la transición a IA, con un máster en IA Generativa y un TFM con un sistema multiagente con RAG. El curso incluye su experiencia de esa "rotación" como hilo personal.

## Público

- Desarrolladores con experiencia (sobre todo backend) que quieren pasar a AI Engineering.
- Se asume que saben programar y usar git. No se asume experiencia previa en ML.
- Cuando ayude, usa analogías con desarrollo backend (APIs, colas, caché, DAOs, logging, APM). No las fuerces.

## Pilares (no negociables)

1. **Desarrollo primero.** Cada concepto termina en código que funciona.
2. **Medir y depurar.** Trazas, métricas (tokens, latencia, coste, tasa de error), iteración guiada por datos y lectura de errores reales. Esto es transversal a todos los módulos, no un tema aislado.
3. **Agnóstico al proveedor.** El núcleo usa abstracciones neutras. Lo específico de una herramienta (Claude, Hugging Face, etc.) va en los anexos.
4. **Sin humo.** Nada de "revolucionario", "potente", "el futuro es ahora". Si algo tiene limitaciones o no compensa, se dice.

## Estructura de cada lección

Todas las lecciones siguen estas secciones, en este orden:

1. **Objetivos**: 3-5 viñetas, verificables.
2. **Teoría**: lo justo para entender la práctica.
3. **Práctica**: código ejecutable en `modulos/NN-*/`.
4. **Mide y depura**: qué instrumentar, qué métrica mirar, cómo iterar.
5. **Errores frecuentes**: incluye al menos una "Anatomía de un error" (error o traza real → cómo leerlo → causa → solución).
6. **Comprueba lo que has entendido**: 3-4 preguntas de aplicar (no de memorizar) con el componente `Autoevaluacion`; cada opción lleva su porqué y, si es incorrecta, qué sección releer. Sin nota ni registro. La lección tiene que ser `.mdx`.
7. **Para profundizar**: fuentes primarias (papers, documentación oficial).

Las lecciones no llevan contenido personal. La experiencia de Alex va en un apartado aparte y opcional, el anexo H ("El proceso del autor"), para que quien lo quiera lo lea y no se mezcle con el aprendizaje (decisión de Alex, 2026-10-31).

## REGLA CRÍTICA: el contenido personal

- **NUNCA inventes experiencias, anécdotas, opiniones ni datos biográficos de Alex.**
- El contenido personal sale **solo** de los ficheros `bitacora/NN-*.md`, que escribe Alex, y se publica solo en el anexo H.
- Puedes corregir el estilo, ordenar e integrar ese texto. **No añadas hechos.**
- Mientras una parte esté vacía, queda como `TODO(alex)`. El anexo H lleva `draft: true` (no se publica) hasta que Alex lo escriba.

## Estilo de escritura

- Español de España, con tuteo y tono directo y técnico.
- Frases cortas. Prosa antes que listas interminables.
- Términos técnicos en inglés cuando es lo habitual en el sector (embedding, chunking, tracing), explicados la primera vez.
- No copies material con copyright (documentación de Anthropic, OpenAI, cursos de terceros). Explica con tus palabras y enlaza la fuente.

## Convenciones técnicas

- **Python** 3.12+, gestionado con **uv** (workspace en la raíz).
- **Scripts** `.py` por defecto. Notebooks solo para exploración visual, y siempre con un script equivalente.
- **Tipado** con type hints y Pydantic para los datos estructurados.
- **Calidad**: ruff (lint y formato) y pytest. El código de las prácticas debe pasar ambos.
- **Secretos**: solo en `.env` (está en `.gitignore`). Se versiona un `.env.example`. Nunca hardcodees claves.
- **Modelos**: los nombres de modelos van en `config/models.toml`, nunca en el código de las prácticas. Cambian cada pocos meses. En el texto solo se nombra el modelo con el que se construyó y probó el curso, dentro de una nota `Revisado: AAAA-MM`, dejando claro que el alumno puede usar el que quiera o pueda.
- **Contenido que caduca**: marca la sección con `Revisado: AAAA-MM`.
- **`curso_core`** es la librería compartida (`packages/curso_core/`) con el cliente LLM con tracing, logging de métricas y utilidades. Crece módulo a módulo. No dupliques esa lógica en las prácticas.

## Web (Astro + Starlight)

- Vive en `site/`. El español es el idioma raíz y la configuración queda preparada para añadir inglés en el futuro.
- **Antes de tocar la configuración, consulta la documentación actual de Astro y Starlight.** Tu conocimiento puede estar desfasado.
- El sidebar se genera a partir de la estructura de `docs/PLAN.md`.

## Forma de trabajar

- Empieza cada tarea proponiendo un plan. Espera confirmación si el cambio es grande.
- Cambios pequeños y verificables. Ejecuta `npm run build` (web) y `uv run pytest` / `uv run ruff check` (código) antes de dar algo por terminado.
- Commits con Conventional Commits (`feat:`, `docs:`, `fix:`…).
- Si algo de este fichero o de `docs/PLAN.md` es ambiguo, pregunta. No supongas.
- Mantén `docs/PLAN.md` actualizado con el estado de cada módulo.

## Referencias

- Temario y estado: `docs/PLAN.md`
- Contribuciones: `CONTRIBUTING.md`
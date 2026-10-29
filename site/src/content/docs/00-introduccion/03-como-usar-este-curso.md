---
title: "Cómo usar este curso"
description: "Cómo usar este curso: estructura, prerrequisitos, ritmo"
---

## Objetivos

Al terminar esta lección podrás:

- Describir las siete secciones de una lección y para qué sirve cada una.
- Comprobar si cumples los prerrequisitos.
- Clonar el repositorio y ejecutar sus comprobaciones (tests, lint y web) en tu máquina.
- Localizar en el repo el código, la configuración y el texto de cada lección.

## Teoría

### Qué vas a encontrar

El curso tiene nueve módulos y unos anexos:

| Módulo | De qué trata |
| --- | --- |
| 0. Introducción | El rol, el curso y tu entorno de trabajo |
| 1. Fundamentos de LLMs | Tokens, contexto, sampling, APIs, coste y latencia |
| 2. Prompting y salida estructurada | Prompts, JSON validado, tool calling y tu primera eval |
| 3. RAG | Conectar el modelo con tus propios datos |
| 4. Evals | Medir la calidad de forma sistemática |
| 5. Agentes | Modelos que usan herramientas en bucle |
| 6. Producción | Arquitectura, observabilidad, seguridad y despliegue |
| 7. Modelos propios | Servir modelos abiertos en tu infraestructura y ajustarlos con fine-tuning (sin entrenar desde cero) |
| 8. Proyecto final | Un sistema completo para tu portafolio |

Los anexos recogen lo específico de herramientas concretas. El núcleo del curso no depende de ningún proveedor.

### Cómo es cada lección

Todas las lecciones siguen las mismas siete secciones, en este orden:

1. **Objetivos.** Lo que sabrás hacer al terminar. Son verificables: úsalos para comprobar si has aprendido algo.
2. **Teoría.** Lo justo para entender la práctica.
3. **Práctica.** Código ejecutable en `modulos/NN-*/`.
4. **Mide y depura.** Qué instrumentar, qué métrica mirar y cómo iterar con datos.
5. **Errores frecuentes.** Incluye al menos una "Anatomía de un error": un error real, cómo leerlo, su causa y la solución.
6. **Bitácora.** La experiencia personal del autor en su paso de backend Java a AI Engineering.
7. **Para profundizar.** Fuentes primarias: papers y documentación oficial.

No te saltes "Mide y depura". Es la sección que más te acerca al trabajo real.

### Prerrequisitos

Necesitas:

- **Saber programar** con soltura en algún lenguaje. Las prácticas están en Python. Si vienes de Java u otro lenguaje, te basta con leer el [tutorial oficial de Python](https://docs.python.org/3/tutorial/) a buen ritmo; el curso no enseña Python desde cero.
- **Usar git** para clonar, hacer commits y trabajar con ramas.
- **Moverte por la terminal.** Las instrucciones dan comandos para macOS, Linux y Windows (PowerShell) cuando difieren.

No necesitas experiencia previa en machine learning ni matemáticas avanzadas.

Para algunas prácticas necesitarás una clave de API de un proveedor de modelos, que puede tener coste. Cuando una práctica tenga alternativa gratuita (por ejemplo, un modelo local), se indicará.

### Ritmo y orden

Los módulos 1 a 6 se apoyan unos en otros: hazlos en orden. El módulo 7 usa las evals del módulo 4 para comparar modelos, así que no lo empieces antes. El proyecto final reúne todo lo anterior.

Dentro de una lección, termina la práctica antes de pasar a la siguiente. Leer sin ejecutar da sensación de avance, pero no deja habilidades.

### Dónde está cada cosa

| Ruta | Qué contiene |
| --- | --- |
| `site/` | Esta web (Astro + Starlight) |
| `modulos/NN-*/` | El código de las prácticas de cada módulo |
| `packages/curso_core/` | La librería compartida: cliente LLM, tracing y métricas. Crece módulo a módulo |
| `config/models.toml` | Los nombres de los modelos que usa el curso |
| `.env.example` | Las variables de entorno que necesitas (claves, observabilidad) |
| `bitacora/` | El texto personal del autor, módulo a módulo |
| `docs/PLAN.md` | El temario y el estado de cada módulo |

Los nombres de modelos no aparecen en el texto ni en el código de las prácticas, solo en `config/models.toml`. Cambian cada pocos meses, y así basta con tocar un fichero.

## Práctica

Clona el repositorio y comprueba que todo funciona. Necesitas [uv](https://docs.astral.sh/uv/) y Node.js; la lección siguiente explica cómo instalarlos si no los tienes.

```sh
git clone https://github.com/alejbrata/dev_to_ia_engineer.git
cd dev_to_ia_engineer

uv sync                # crea el entorno virtual e instala las dependencias
uv run pytest          # ejecuta los tests
uv run ruff check      # pasa el linter
```

Si todo va bien, pytest termina con una línea como `10 passed` y ruff con `All checks passed!`. El número de tests crecerá con el curso.

Ahora arranca la web en local:

```sh
cd site
npm install
npm run dev
```

Abre la dirección que aparece en la terminal. Cualquier cambio en `site/src/content/docs/` se ve al momento.

## Mide y depura

Los tests y el linter son tu primera fuente de datos. Aprende a sacarles más información:

```sh
uv run pytest -v               # un resultado por test, no solo puntos
uv run pytest --durations=5    # los cinco tests más lentos
uv run pytest -x               # para en el primer fallo
```

Las mismas comprobaciones se ejecutan en GitHub Actions con cada push. Si un cambio pasa en tu máquina y falla allí, compara versiones (de Python, Node o dependencias) antes que nada: es la causa más habitual.

## Errores frecuentes

**Ejecutar los comandos desde la carpeta equivocada.** Los comandos de Python (`uv ...`) se ejecutan desde la raíz del repo. Los de la web (`npm ...`), desde `site/`. Si un comando no encuentra el fichero de proyecto, mira primero dónde estás.

**Leer sin ejecutar.** Cada práctica se diseña para que algo falle o sorprenda. Si no la ejecutas, te pierdes la parte que enseña.

### Anatomía de un error: la web y el plan no coinciden

El repo tiene un test que comprueba que las páginas de la web coinciden con el temario de `docs/PLAN.md`. Si renombras una página a mano, falla:

```text
FAILED tests/test_plan_sync.py::test_paginas_coinciden_con_el_plan

>       assert existentes == esperadas
E       AssertionError: assert {'00-introduc...exto.md', ...} == {'00-introduc...exto.md', ...}
E
E         Extra items in the left set:
E         '03-rag/05-rerankers.md'
E         Extra items in the right set:
E         '03-rag/05-reranking.md'
E         Use -v to get more diff
```

**Cómo leerlo.** pytest compara dos conjuntos. A la izquierda, `existentes`: las páginas que hay en disco. A la derecha, `esperadas`: las que se derivan del plan. "Extra items in the left set" es lo que sobra en disco; "in the right set", lo que falta.

**Causa.** Alguien renombró `05-reranking.md` a `05-rerankers.md` sin tocar el plan.

**Solución.** Decide cuál es la fuente de verdad. Si el nombre bueno es el del plan, deshaz el cambio de nombre. Si quieres cambiar el título, edita `docs/PLAN.md` y regenera con `uv run python scripts/plan_sync.py`. El patrón es el mismo que en cualquier sistema con datos derivados: se cambia el origen y se regenera, no al revés.

## Bitácora

TODO(alex)

## Para profundizar

- [Documentación de uv](https://docs.astral.sh/uv/): gestión de Python, entornos y dependencias.
- [Documentación de pytest](https://docs.pytest.org/).
- [Documentación de GitHub Actions](https://docs.github.com/actions).
- [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/): el formato de mensajes de commit que usa el repo.
- [CONTRIBUTING.md](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/CONTRIBUTING.md): cómo proponer cambios al curso.

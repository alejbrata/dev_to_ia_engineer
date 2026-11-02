---
title: "C. Herramientas y estrategias de desarrollo con IA"
description: "Herramientas y estrategias de desarrollo con IA: agentes de código, cómo trabajar con ellos sin perder el control, técnicas de razonamiento como Graph of Thoughts y repositorios útiles"
---

:::note[Revisado: 2026-11]
Las herramientas de esta página cambian cada pocos meses: nombres, precios y funciones. Lo que dura son las ideas de fondo (contexto, verificación, revisión). Comprueba los detalles en la documentación de cada una.
:::

Este anexo trata de usar la IA para **desarrollar**, no de desarrollar sistemas con IA, que es el resto del curso. Si vienes de backend, es probable que ya uses algún asistente de código. Aquí está lo que conviene saber para que te ahorre trabajo y no te lo cree.

<!-- Sección personal, la escribe Alex:
## Mi forma de trabajar

TODO(alex)
-->

## Agentes de código

Hay tres niveles de ayuda, y conviene saber en cuál estás:

- **Autocompletado.** El modelo propone la siguiente línea o el siguiente bloque mientras escribes. Tú decides cada línea.
- **Chat en el editor.** Le preguntas o le pides un cambio y te propone un diff. Tú decides cada cambio.
- **Agente.** Le das una tarea y él lee el repositorio, edita varios ficheros, ejecuta comandos y tests, y repite hasta terminar. Tú decides la tarea y revisas el resultado.

Un agente de código es el bucle del módulo 5 (lección 5.03) aplicado a tu repositorio: herramientas para leer, buscar, editar y ejecutar, y un modelo que decide qué hacer después. Por eso le aplican las mismas lecciones: necesita contexto, se equivoca de formas reconocibles y hay que vigilar qué puede hacer con sus herramientas (lección 5.11).

Algunos de los más usados, a noviembre de 2026: [Claude Code](https://code.claude.com/docs/en/overview) (terminal, editores y web; el anexo A trata la API de Claude), [GitHub Copilot](https://docs.github.com/en/copilot) (integrado en GitHub y en los editores), [Cursor](https://cursor.com/docs) (un editor construido alrededor del agente), y opciones abiertas como [Aider](https://github.com/Aider-AI/aider), [Codex CLI](https://github.com/openai/codex) o [Continue](https://github.com/continuedev/continue), que permiten usar modelos de distintos proveedores, también locales.

## Cómo trabajar con un agente sin perder el control

### Dale el contexto que no tiene

El agente no sabe las convenciones de tu proyecto, qué comandos verifican un cambio ni qué no se puede tocar. La forma estándar de decírselo es un fichero en la raíz del repositorio que el agente lee al empezar: `CLAUDE.md` en Claude Code, `AGENTS.md` en el formato abierto que adoptan cada vez más herramientas ([agents.md](https://agents.md/)), o las reglas de cada editor.

Lo que funciona en ese fichero es lo mismo que en un buen documento de incorporación a un equipo: qué es el proyecto, cómo se ejecuta y se prueba, las convenciones (nombres, estructura, estilo), y las reglas que no se negocian. Este repositorio tiene el suyo, [`CLAUDE.md`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/CLAUDE.md), y puedes leerlo como ejemplo: incluye, por ejemplo, que los nombres de modelo solo van en `config/models.toml` y qué comandos hay que pasar antes de dar algo por terminado.

### Pide un plan antes de los cambios grandes

Para una tarea que toca varios ficheros, pide primero el plan y revísalo: qué ficheros va a cambiar, en qué orden y cómo lo va a verificar. Corregir un plan cuesta un minuto; deshacer cuarenta ficheros editados en la dirección equivocada, bastante más. Muchas herramientas tienen un modo específico para esto, en el que el agente investiga y propone sin editar nada.

### Que el agente pueda comprobar su trabajo

Un agente rinde mucho más cuando puede verificar lo que hace: tests, un linter, un build, un script que compare una salida con la esperada. Es el mismo principio que la eval del módulo 4: sin una forma de medir, el agente (como cualquiera) da por bueno lo que parece bueno. Si tu proyecto no tiene tests, escribirlos es lo primero que conviene pedirle, y revisarlos a fondo, porque serán el criterio de todo lo demás.

### Revisa como revisarías un pull request

El código generado se revisa igual que el de un compañero: el diff completo, ejecutándolo, y con especial cuidado en lo que el agente no puede ver. Los fallos típicos:

- **Tests que se ajustan al código** en lugar de comprobar el comportamiento, o que se debilitan para que pasen.
- **Cambios fuera de lo pedido**: refactorizaciones que nadie pidió, ficheros tocados de paso.
- **Dependencias nuevas** que no hacían falta, o con versiones inventadas.
- **APIs inventadas o desfasadas**: el modelo recuerda la versión de su entrenamiento, no la que usas. Pídele que consulte la documentación actual, como hace este curso con Astro y Starlight.
- **Secretos y datos**: claves pegadas en el código, o un `.env` añadido al commit (lección 6.04).

### Limita lo que puede hacer

Un agente que ejecuta comandos puede borrar ficheros, hacer `push` o lanzar algo caro. Las herramientas permiten decidir qué acciones necesitan tu aprobación; usa ese control. Cuanto más autónomo lo dejes, más importante es que trabaje en una rama, en un entorno aislado o en una copia (un *worktree* de git, un contenedor), y que lo que llega a la rama principal pase tu revisión y el CI. Es la misma idea que la aprobación humana de los grafos de estado (lección 5.05).

### Cambios pequeños

Cuanto más larga es la tarea, más contexto acumula el agente y más difícil es revisar lo que ha hecho (lección 5.07). Divide el trabajo en cambios pequeños y verificables, con un commit cada uno, igual que harías a mano: si uno sale mal, se deshace sin arrastrar a los demás.

## Técnicas de razonamiento: de chain-of-thought a Graph of Thoughts

La lección 1.07 trata los modelos que razonan antes de responder. Antes de que existieran, el razonamiento se conseguía desde el prompt o desde el código, y esas técnicas siguen siendo útiles para entender qué pasa y para tareas en las que conviene controlar el proceso:

- **Chain-of-thought** ([Wei et al., 2022](https://arxiv.org/abs/2201.11903)): pedir al modelo que razone paso a paso antes de dar la respuesta. Es lo que los modelos que razonan hacen ahora por su cuenta.
- **Self-consistency** ([Wang et al., 2022](https://arxiv.org/abs/2203.11171)): generar varios razonamientos y quedarse con la respuesta más votada. Más llamadas a cambio de más fiabilidad.
- **Tree of Thoughts** ([Yao et al., 2023](https://arxiv.org/abs/2305.10601)): explorar varias ramas de razonamiento, evaluar cada una y seguir las prometedoras, con vuelta atrás.
- **Graph of Thoughts** ([Besta et al., 2023](https://arxiv.org/abs/2308.09687)): generalizar el árbol a un grafo.

### Graph of Thoughts

En Graph of Thoughts (GoT), cada "pensamiento" (una solución parcial generada por el modelo) es un nodo, y las aristas son dependencias entre ellos. Lo que añade sobre el árbol son operaciones que un árbol no permite:

- **Agregar**: combinar varios pensamientos en uno mejor. Por ejemplo, fusionar resúmenes parciales o mezclar listas ordenadas por separado.
- **Refinar**: volver sobre un pensamiento con realimentación, en un bucle.
- **Generar**: ramificar un pensamiento en varios, como en el árbol.

El ejemplo del artículo es ordenar una lista larga: el modelo ordena trozos por separado (generar), los mezcla de dos en dos (agregar) y corrige los errores de cada mezcla (refinar), como un *merge sort* hecho con llamadas al modelo. En ordenación, los autores miden un 62 % más de calidad que Tree of Thoughts con más de un 31 % menos de coste. La implementación oficial está en [spcl/graph-of-thoughts](https://github.com/spcl/graph-of-thoughts).

Dos matices antes de usarlo:

- **Es un workflow, no un prompt.** El grafo lo define y lo ejecuta tu código, y cada nodo es una llamada al modelo. Es la misma estructura que los grafos de estado de la lección 5.05: puedes montarlo con ese motor o con LangGraph.
- **Compensa en tareas que se descomponen y se recomponen**: ordenar, fusionar documentos, combinar resultados de varias fuentes. Para preguntas normales, un modelo que razona (lección 1.07) da lo mismo con una llamada. Como siempre en el curso: mide la calidad y el número de llamadas frente a la opción simple antes de quedarte con la compleja.

## Repositorios útiles

- [anthropics/claude-code](https://github.com/anthropics/claude-code), [openai/codex](https://github.com/openai/codex), [Aider-AI/aider](https://github.com/Aider-AI/aider) y [continuedev/continue](https://github.com/continuedev/continue): agentes de código, con sus incidencias y sus registros de cambios, útiles para ver cómo evolucionan.
- [agents.md](https://agents.md/): el formato abierto para el fichero de contexto de los agentes, con ejemplos.
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers): servidores MCP (lección 5.10) que puedes conectar a tu agente de código: sistemas de ficheros, git, bases de datos...
- [spcl/graph-of-thoughts](https://github.com/spcl/graph-of-thoughts): la implementación de referencia de Graph of Thoughts.

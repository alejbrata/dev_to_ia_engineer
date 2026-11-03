---
title: "C. Herramientas y estrategias de desarrollo con IA"
description: "Herramientas y estrategias de desarrollo con IA: agentes de código, cómo trabajar con ellos sin perder el control, técnicas de razonamiento como Graph of Thoughts y repositorios útiles"
---

:::note[Revisado: 2026-11]
Las herramientas de esta página cambian cada pocos meses: nombres, precios y funciones. Lo que dura son las ideas de fondo (contexto, verificación, revisión). Comprueba los detalles en la documentación de cada una.
:::

Este anexo trata de usar la IA para **desarrollar**, no de desarrollar sistemas con IA, que es el resto del curso. Si vienes de backend, es probable que ya uses algún asistente de código. Aquí está lo que conviene saber para que te ahorre trabajo y no te lo cree.

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

### Medido con el modelo local

[`graph_of_thoughts.py`](https://github.com/alejbrata/dev_to_ia_engineer/blob/main/modulos/c-desarrollo-con-ia/graph_of_thoughts.py) repite el ejemplo del artículo con el modelo de 7B del curso: ordenar listas de dígitos del 0 al 9, con repetidos. Compara tres formas:

- **Una llamada.** La lista entera, ordenada de una vez.
- **Una y corregir.** Lo mismo y, si el código encuentra errores, una llamada más con los problemas. Sirve de control: separa el efecto de corregir del de descomponer.
- **Graph of Thoughts.** Cuatro trozos ordenados por separado (generar), mezclados de dos en dos (agregar) y, tras cada paso con errores, una corrección con la realimentación del código (refinar).

Los errores los cuenta el código: elementos que faltan o sobran frente a la original, más pares contiguos desordenados. Los prompts están en `prompts/razonamiento/`.

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/c-desarrollo-con-ia/graph_of_thoughts.py             # unos 50 minutos en CPU
uv run python modulos/c-desarrollo-con-ia/graph_of_thoughts.py --grabadas  # la salida grabada
```

```text
1. Ordenar 8 listas de dígitos de cada tamaño, con qwen2.5:7b
   método             tamaño  errores  perfectas  llamadas  tokens  s/lista
   una llamada            32      4.5      0 de 8       1.0     265     13.6
   una y corregir         32      4.2      0 de 8       2.0     678     29.5
   graph of thoughts      32      5.1      0 de 8       9.2    1924     75.7
   una llamada            64     15.1      0 de 8       1.0     426     24.9
   una y corregir         64     15.0      0 de 8       2.0    1078     51.6
   graph of thoughts      64     20.0      0 de 8      11.0    3466    165.0
   (errores, llamadas, tokens y segundos: media por lista)

2. Respuestas sin JSON válido: 1

3. Un caso de 64 dígitos
   original:          7063812066503008913193442176104714285124000348559097765823694022
   correcta:          0000000000011111112222222333333444444455555666666777778888899999
   una llamada:       00000000001111111222233333444445555666667777888999  (14 errores)
      faltan 0 (x1), 2 (x3), 3 (x1), 4 (x2), 5 (x1), 6 (x1), 7 (x1), 8 (x2), 9 (x2)
   una y corregir:    000000000011111112222333334444455556666677778888999  (13 errores)
      faltan 0 (x1), 2 (x3), 3 (x1), 4 (x2), 5 (x1), 6 (x1), 7 (x1), 8 (x1), 9 (x2)
   graph of thoughts: 00000011111122222333344444555556666777788889999  (17 errores)
      faltan 0 (x5), 1 (x1), 2 (x2), 3 (x2), 4 (x2), 6 (x2), 7 (x1), 8 (x1), 9 (x1)
```

Cómo leerlo:

- **Con este modelo, el grafo no mejora: empeora.** Con 32 dígitos, 5,1 errores de media frente a 4,5 con una llamada; con 64, 20,0 frente a 15,1. Y cuesta entre 7 y 8 veces más tokens, y entre 5 y 7 veces más tiempo. Ninguna lista quedó perfecta con ningún método.
- **El modelo no desordena: pierde elementos.** Sumando las 16 listas, de los errores de una llamada, 149 son dígitos que faltan, 8 que sobran y 0 pares desordenados. Siempre devuelve una lista ordenada, pero más corta, como en el caso de arriba: se salta repetidos. El grafo descompone justo lo que el modelo ya hacía bien (ordenar) y añade pasos de mezcla, y en cada mezcla vuelve a perder elementos: 195 faltan con el grafo.
- **Corregir casi no arregla nada.** Con la lista de lo que falta delante, el modelo apenas recupera elementos: de 4,5 a 4,2 errores, y de 15,1 a 15,0. Refinar solo sirve si el modelo es capaz de hacer la corrección.

No contradice el artículo, que usó otro modelo y un grafo con más ramas, sino que muestra su condición: Graph of Thoughts ayuda cuando el modelo hace bien cada paso pequeño y se equivoca en el grande. Si el modelo falla también en los pasos pequeños (aquí, mezclar dos listas sin perder elementos), descomponer multiplica los fallos. Y una advertencia sobre el ejemplo: ordenar es una tarea que el código hace perfecta en microsegundos. Sirve para medir la técnica porque se puntúa sola. En una tarea real, el patrón vale cuando cada paso es difícil de programar pero fácil de comprobar.

## Repositorios útiles

- [anthropics/claude-code](https://github.com/anthropics/claude-code), [openai/codex](https://github.com/openai/codex), [Aider-AI/aider](https://github.com/Aider-AI/aider) y [continuedev/continue](https://github.com/continuedev/continue): agentes de código, con sus incidencias y sus registros de cambios, útiles para ver cómo evolucionan.
- [agents.md](https://agents.md/): el formato abierto para el fichero de contexto de los agentes, con ejemplos.
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers): servidores MCP (lección 5.10) que puedes conectar a tu agente de código: sistemas de ficheros, git, bases de datos...
- [spcl/graph-of-thoughts](https://github.com/spcl/graph-of-thoughts): la implementación de referencia de Graph of Thoughts.

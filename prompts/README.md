# Prompts del curso

Cada fichero `.md` de esta carpeta es un prompt versionado. Puedes leerlos, copiarlos y adaptarlos: son parte del material del curso.

## Formato

```markdown
---
version: 1
descripcion: Para qué sirve este prompt.
variables: ticket
---

## Sistema
Instrucciones generales (rol, contexto, criterios, formato).

## Ejemplos
### Usuario
Un ejemplo de entrada.
### Asistente
La respuesta que esperas para ese ejemplo.

## Usuario
El mensaje con las variables: {{ticket}}
```

- `## Sistema` y `## Ejemplos` son opcionales. `## Usuario` es obligatoria.
- Las variables se escriben `{{nombre}}` y se declaran en la cabecera.
- Sube `version` cada vez que cambies el prompt: queda registrada en las trazas de `curso_core` (`tickets/completo@v1`).

Para usarlos desde Python:

```python
from curso_core import ClienteLLM, prompts

prompt = prompts.cargar("tickets/completo")
respuesta = ClienteLLM().chat(prompts.renderizar(prompt, ticket="La búsqueda va lenta."))
```

## Contenido

| Carpeta | Para qué |
| --- | --- |
| `tickets/` | Clasificar tickets de incidencias (módulo 2) |

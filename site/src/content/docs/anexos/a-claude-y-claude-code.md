---
title: "A. Claude y Claude Code"
description: "Claude y Claude Code: consejos prácticos desde el uso real (sin copiar documentación oficial)"
---

## Consejos desde el uso real

TODO(alex)

## La API de Claude

:::note[Revisado: 2026-10]
Modelos y precios publicados por Anthropic en octubre de 2026. Cambian a menudo: consulta la [página de precios](https://platform.claude.com/docs/en/about-claude/pricing) y la de [modelos](https://platform.claude.com/docs/en/about-claude/models/overview). El código de esta sección no se ha ejecutado en el curso.
:::

Este apartado es la parte de Claude del [anexo G](../g-apis-comerciales/), que explica cuándo compensa una API comercial frente al modelo local y cómo medirlo.

Anthropic tiene su propia API (Messages) y SDK oficiales para Python y otros lenguajes. No usa el formato de OpenAI que habla `curso_core`, así que hoy no basta con cambiar `config/models.toml`: integrarla como proveedor del curso exige un dialecto nuevo en el cliente. Mientras tanto, puedes llamarla directamente con su SDK.

Instala el SDK y pon la clave en `.env` (variable `ANTHROPIC_API_KEY`, ya prevista en `.env.example`):

```sh title="Terminal de VS Code · raíz del repo"
uv add anthropic
```

Una llamada mínima, con el mismo esquema que el resto del curso (un mensaje de usuario, una respuesta de texto):

```python
import anthropic

client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno

respuesta = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "¿Qué es un pool de conexiones?"}],
)
for bloque in respuesta.content:
    if bloque.type == "text":
        print(bloque.text)
print(respuesta.usage.input_tokens, respuesta.usage.output_tokens)
```

Diferencias con el formato de OpenAI que conviene conocer:

- **La respuesta es una lista de bloques** (`text`, `thinking`, `tool_use`…), no un único texto. Recorre los bloques y quédate con los de tipo `text`.
- **El mensaje de sistema va aparte**, en el parámetro `system`, no como un mensaje más de la lista.
- **`max_tokens` es obligatorio** en cada llamada.
- **Los tokens están en `usage`** (`input_tokens`, `output_tokens`): con ellos y los precios calculas el coste, igual que hace `curso_core` con sus trazas.

Modelos y precios en USD por millón de tokens de entrada y de salida, a octubre de 2026:

| Modelo | Identificador | Entrada | Salida |
| --- | --- | --- | --- |
| Claude Haiku 5.5 | `claude-haiku-5-5` | 0,10 | 0,50 |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | 2,00 | 10,00 |
| Claude Opus 5.5 | `claude-opus-5-5` | 4,00 | 20,00 |

Para comparar con el modelo local del curso, empieza por el más barato: si el pequeño ya resuelve tu caso, no hace falta pagar más. Y mide con tu eval, como en el anexo G, antes de decidir.

## Claude Code

TODO(alex)

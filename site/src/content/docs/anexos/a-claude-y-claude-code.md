---
title: "A. Claude y Claude Code"
description: "Claude y Claude Code: consejos prácticos desde el uso real (sin copiar documentación oficial)"
---

:::note[En preparación]
Las secciones de consejos desde el uso real y de Claude Code aún no están escritas. Mientras tanto, aquí tienes cómo usar la API de Claude desde el curso.
:::

<!-- Sección personal, la escribe Alex:
## Consejos desde el uso real

TODO(alex)
-->

## La API de Claude

:::note[Revisado: 2026-10]
Modelos y precios publicados por Anthropic en octubre de 2026. Cambian a menudo: consulta la [página de precios](https://platform.claude.com/docs/en/about-claude/pricing) y la de [modelos](https://platform.claude.com/docs/en/about-claude/models/overview). La integración con `curso_core` tiene tests, pero aún no se ha probado contra la API real con una clave.
:::

:::tip[Opcional]
No necesitas Claude ni ninguna API de pago para seguir el curso. Este apartado es para quien quiera comparar o ya tenga acceso. Es la parte de Claude del [anexo G](../g-apis-comerciales/), que explica cuándo compensa una API comercial frente al modelo local y cómo medirlo.
:::

### Desde las prácticas del curso

Anthropic tiene su propia API (Messages), que no usa el formato de OpenAI. `curso_core` la habla con el SDK oficial de Anthropic (el proveedor de tipo `anthropic`), así que se usa igual que el resto: con un rol de `config/models.toml`.

1. Pon tu clave en `.env`, en la variable `ANTHROPIC_API_KEY` (ya prevista en `.env.example`).
2. Usa el rol `chat_claude`. Por ejemplo, para comparar el sistema del módulo 4 con Claude:

```sh title="Terminal de VS Code · raíz del repo"
uv run python modulos/04-evals/con_api.py --rol chat_claude
```

Sin la clave, se para antes de llamar a nada:

```text
No se puede usar el rol chat_claude: Falta la variable de entorno ANTHROPIC_API_KEY en .env
```

Lo que el cliente hace distinto con Claude, y por qué:

- **No envía temperatura, `top_p` ni semilla.** La versión actual de la API los rechaza. Como en OpenAI, eso hace que las respuestas puedan variar entre ejecuciones.
- **Pone siempre `max_tokens`**, porque en Claude es obligatorio: el de la práctica o, si no lo fija, 16000.
- **Pide el esquema JSON estricto** en la salida estructurada (`extraer`), con los objetos cerrados, igual que en OpenAI.
- **Activa la reserva automática ante rechazos** en los modelos que la admiten: si el modelo declina una petición por sus filtros de seguridad, la API la repite con otro modelo dentro de la misma llamada.
- **No admite herramientas ni logprobs** en esta versión de `curso_core`: las prácticas que los usan (módulos 1 y 2) siguen necesitando otro proveedor.

### Llamar al SDK directamente

Si quieres usar Claude fuera de las prácticas, una llamada mínima con el SDK (ya está instalado con el curso):

```python
import anthropic

client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno

respuesta = client.messages.create(
    model="claude-opus-5-5",
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

El rol `chat_claude` usa Claude Opus 5.5. Para probar uno más barato, cambia `model` en ese rol de `config/models.toml` y añade su precio en la sección `[precios]`, para que las trazas calculen el coste. Y mide con tu eval, como en el anexo G, antes de decidir.

<!-- Sección personal, la escribe Alex:
## Claude Code

TODO(alex)
-->

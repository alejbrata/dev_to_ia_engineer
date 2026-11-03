# Postmortem: el modelo de 1,5B como principal

## Resumen
Se propuso pasar el modelo principal del asistente de qwen2.5:7b a qwen2.5:1.5b, más rápido.
En sombra perdía 12 casos de la eval y ganaba 0 (p = 0.000). En canario, las
señales de producción no pidieron volver atrás.

## Impacto
El canario debía llevar el 25 % de las preguntas. Llevó 12 de las 27
distintas del tráfico y el 55 % de las peticiones: con pocas preguntas, el
reparto no es uniforme, y las que más se repetían cayeron de su lado. Tras volver
atrás, 12 respuestas del vigente salieron de la caché con el modelo del candidato.

## Causa
La clave de la caché era la huella del sistema, que no cambia si el modelo se elige por
configuración. Las dos versiones compartían las mismas claves.

## Qué funcionó
La evaluación en sombra detectó la pérdida de calidad antes de servir una sola respuesta.

## Acciones
- La clave de la caché incluye el modelo que responde (`Asistente.version_cache`).
- Ningún cambio de modelo pasa a canario sin la eval en sombra.
- Revisar qué señales de producción habrían detectado la pérdida de calidad.

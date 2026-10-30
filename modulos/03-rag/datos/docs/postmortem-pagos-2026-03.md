# Postmortem: caída de pagos (marzo de 2026)

## Resumen

El 12 de marzo de 2026, el servicio de pagos estuvo caído 47 minutos. Ningún cliente pudo pagar.

## Causa raíz

Una nueva versión del conector de pasarela abría una conexión a la base de datos por cada reintento y no la devolvía al pool. Con el tráfico de la mañana, el pool se agotó en 20 minutos y la base de datos empezó a rechazar conexiones con too many connections.

## Qué funcionó y qué no

La alerta saltó a los 3 minutos. La vuelta a la versión anterior tardó 40 minutos porque nadie de guardia conocía el procedimiento.

## Acciones

- Se subió el límite del pool de 100 a 200 conexiones.
- Se escribió el runbook de pagos sin conexiones a la base de datos.
- Se añadió una alerta cuando el pool supera el 80 % de uso.

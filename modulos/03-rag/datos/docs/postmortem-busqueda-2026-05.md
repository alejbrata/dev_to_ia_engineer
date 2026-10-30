# Postmortem: productos nuevos sin indexar (mayo de 2026)

## Resumen

Del 8 al 9 de mayo de 2026, los productos nuevos no aparecieron en la búsqueda durante 19 horas.

## Causa raíz

El disco de un nodo de OpenSearch llegó al 95 % y el índice dejó de aceptar escrituras. La alerta de disco existía, pero estaba configurada solo para el entorno de pruebas.

## Acciones

- La alerta de disco al 85 % se activó en producción.
- Se automatizó el borrado de índices de más de 30 días.

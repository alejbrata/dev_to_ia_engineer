# Runbook: cobros duplicados

Usa este runbook cuando los clientes reclamen cobros repetidos del mismo pedido.

## Mitigación

Si el problema empezó con un despliegue de pagos, vuelve a la versión anterior de inmediato: los cobros duplicados suelen venir de reintentos sin clave de idempotencia. Después, saca la lista de pedidos cobrados más de una vez (por id de pedido) y pásala al equipo de negocio para los reembolsos.

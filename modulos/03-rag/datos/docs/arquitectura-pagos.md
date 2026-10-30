# Arquitectura del servicio de pagos

El servicio de pagos cobra los pedidos a través de una pasarela de pago externa y guarda cada transacción en PostgreSQL.

## Componentes

- API de pagos: recibe las peticiones de cobro desde el servicio de pedidos.
- Conector de pasarela: llama a la pasarela externa por HTTPS con reintentos.
- PgBouncer: gestiona el pool de conexiones a PostgreSQL. El límite actual es de 200 conexiones.

## Dependencias críticas

Si PostgreSQL o la pasarela externa fallan, no se puede cobrar ningún pedido. Por eso pagos tiene el SLA más exigente de la plataforma.

## Credenciales

El token de la API del banco caduca cada 90 días. Su renovación está en el runbook de credenciales de pagos.

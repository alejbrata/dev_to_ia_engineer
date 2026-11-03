# Runbook: pagos sin conexiones a la base de datos

Usa este runbook cuando el servicio de pagos devuelva errores 500 y en los logs aparezca too many connections contra PostgreSQL.

## Diagnóstico

1. Abre el panel de PgBouncer y mira el número de conexiones activas.
2. Comprueba si ha habido un despliegue de pagos en la última hora: la mayoría de incidentes de este tipo empiezan con una versión que no devuelve las conexiones al pool.
3. Revisa si alguna consulta lleva más de 30 segundos ejecutándose.

## Mitigación

Si hubo un despliegue reciente, vuelve a la versión anterior: es la mitigación más rápida. Si no lo hubo, reinicia PgBouncer de forma ordenada, una réplica cada vez, para liberar las conexiones bloqueadas.

No subas el límite del pool por encima de 200 conexiones sin hablar con el equipo de bases de datos: PostgreSQL tiene un máximo de 250 conexiones y el resto de procesos necesitan margen.

## Escalado

Si en 15 minutos los cobros no se recuperan, escala al responsable del equipo Cobros.

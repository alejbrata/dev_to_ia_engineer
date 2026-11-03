# Runbook: el índice de búsqueda se queda sin disco

Usa este runbook cuando el índice de búsqueda deje de indexar productos nuevos por falta de espacio en disco.

## Diagnóstico

OpenSearch deja de escribir cuando el disco de un nodo supera el 95 % de uso. Hay una alerta a partir del 85 %.

## Mitigación

1. Borra los índices antiguos de más de 30 días: se crean uno por día y nadie los consulta.
2. Comprueba que el indexador vuelve a escribir.
3. Si el disco sigue por encima del 85 % tras la limpieza, pide más espacio al equipo de plataforma.

Los productos que no se indexaron durante el problema se reindexan solos en el siguiente ciclo nocturno, a las 03:00.

# Monitorización y alertas

Cada servicio tiene un panel con latencia, tasa de errores y saturación.

## Alertas principales

| Alerta | Condición |
| --- | --- |
| PagosLatenciaP95Alta | latencia p95 de pagos por encima de 800 ms durante 5 minutos |
| PagosErroresAltos | más del 2 % de errores en pagos durante 5 minutos |
| PoolConexionesPagos | pool de PgBouncer por encima del 80 % |
| RedisMemoriaNotificaciones | memoria de Redis por encima del 80 % |
| DiscoBusqueda | disco de un nodo de OpenSearch por encima del 85 % |
| ReplicaCatalogoRetraso | retraso de la réplica del catálogo por encima de 5 minutos |

## Ruido

Una alerta que salta sin requerir acción se revisa en la reunión semanal: o se corrige el umbral o se elimina.

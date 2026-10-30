# Runbook: retraso de la réplica del catálogo

Usa este runbook cuando la réplica de lectura del catálogo vaya con retraso y la tienda muestre precios antiguos.

## Umbrales

Un retraso de hasta 30 segundos es normal. A partir de 5 minutos salta una alerta. A partir de 15 minutos, los precios que ve la tienda pueden diferir de los reales y conviene avisar al equipo de atención al cliente.

## Mitigación

1. Comprueba si hay alguna consulta pesada en la réplica que bloquee la replicación.
2. Si la hay, cancélala.
3. Si el retraso sigue creciendo, redirige temporalmente las lecturas de precios a la base de datos principal con el interruptor precios_desde_principal.

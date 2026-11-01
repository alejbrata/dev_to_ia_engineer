# Runbook: precios erróneos tras una importación

Usa este runbook cuando los precios de la tienda cambien de forma anómala justo después de una importación de precios desde el ERP.

## Diagnóstico

1. Busca en los logs del catálogo la última importación de precios y cuántos productos cambió.
2. Comprueba si hay avisos de cambios de precio de más del 50 %.

## Mitigación

Revierte la importación de precios: vuelve a aplicar el lote anterior desde el panel de importaciones. Después, congela la sincronización del catálogo con el ERP hasta que el equipo de precios revise el lote erróneo; si no la congelas, la siguiente sincronización volverá a aplicarlo.

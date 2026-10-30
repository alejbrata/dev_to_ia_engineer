# Runbook: fichas de producto sin imágenes

Usa este runbook cuando las fichas de producto del catálogo salgan sin imágenes.

## Diagnóstico

1. Abre una ficha afectada y copia la ruta de la imagen.
2. Pide esa ruta directamente a la CDN. Si devuelve 404, la ruta no existe en la CDN.
3. Comprueba si ha habido un despliegue del catálogo: los cambios en el formato de las rutas son la causa más habitual.

## Mitigación

Si el problema empezó con un despliegue, vuelve a la versión anterior. Después, corrige la generación de rutas y vuelve a desplegar en un canario antes de llegar al 100 %.

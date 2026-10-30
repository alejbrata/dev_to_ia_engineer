# Arquitectura del servicio de catálogo

El catálogo guarda los productos, sus precios y sus imágenes.

## Lectura y escritura

Las escrituras (altas de productos, cambios de precio) van a la base de datos principal. Las lecturas de la tienda van a una réplica de lectura para no cargar la principal. Un retraso de la réplica hace que la tienda muestre datos antiguos.

## Imágenes

Las imágenes se sirven desde una CDN. El catálogo solo guarda la ruta de cada imagen; si la ruta cambia en un despliegue y la CDN no la conoce, las fichas salen sin imagen.

## Panel de administración

El panel de administración del catálogo lo usan los editores. Requiere el rol editor en el servicio de usuarios.

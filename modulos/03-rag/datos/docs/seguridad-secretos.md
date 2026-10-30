# Gestión de secretos

Todos los secretos (contraseñas, tokens, claves de API) se guardan en el gestor de secretos. Nunca en el código, en ficheros de configuración del repositorio ni en variables escritas a mano en el despliegue.

## Rotación

Los secretos se rotan como mínimo cada 90 días. Los que tienen caducidad fijada por un proveedor externo (bancos, Google, Apple) siguen el plazo del proveedor.

## Si un secreto se filtra

1. Revócalo inmediatamente en su origen.
2. Genera uno nuevo y guárdalo en el gestor de secretos.
3. Avisa al equipo de seguridad, aunque creas que nadie lo ha usado.

Borrar el secreto del repositorio no es suficiente: sigue en el historial.

# Runbook: no llegan las notificaciones push

Usa este runbook cuando no llegue ninguna notificación push a los móviles.

## Causa habitual

Las credenciales de los proveedores de push caducan una vez al año. Cuando caducan, todos los envíos fallan con un error de autenticación del proveedor.

## Solución

1. Genera credenciales nuevas en las consolas de Apple y de Google.
2. Guárdalas en el gestor de secretos, en la ruta notificaciones/push.
3. Reinicia los pods de notificaciones.

Las notificaciones push que fallaron durante la caducidad no se reenvían.

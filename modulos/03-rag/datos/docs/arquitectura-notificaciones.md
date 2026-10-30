# Arquitectura del servicio de notificaciones

Documento revisado en enero de 2025.

El servicio de notificaciones envía emails, SMS y notificaciones push a partir de los eventos que llegan a su cola en Redis.

## Canales

- Email: a través de un servidor SMTP propio, por el puerto 587.
- SMS: a través de un proveedor externo.
- Push: a través de los proveedores de Apple y Google, con credenciales propias.

## Disponibilidad

El objetivo de disponibilidad de notificaciones es del 99,9 % mensual.

## Cola

Si la cola de Redis se llena, los mensajes nuevos se descartan. Hay una alerta cuando la memoria de Redis supera el 80 %.

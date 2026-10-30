---
version: 1
descripcion: Pide un formato de respuesta y da los valores posibles, sin explicar qué significan.
variables: ticket
---

## Usuario

Clasifica este ticket de soporte.

Responde exactamente con estas tres líneas y nada más:
categoria: <base_de_datos | red | despliegue | autenticacion | rendimiento | otro>
severidad: <baja | media | alta | critica>
servicio: <pagos | usuarios | catalogo | notificaciones | busqueda>

Ticket:
{{ticket}}

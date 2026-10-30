# Arquitectura general de la plataforma

La plataforma de comercio electrónico se compone de cinco servicios: pagos, usuarios, catalogo, notificaciones y busqueda. Cada servicio se despliega de forma independiente en Kubernetes y tiene un equipo responsable.

## Servicios y equipos

| Servicio | Equipo responsable | Base de datos principal |
| --- | --- | --- |
| pagos | Cobros | PostgreSQL |
| usuarios | Identidad | PostgreSQL |
| catalogo | Catálogo | PostgreSQL con réplica de lectura |
| notificaciones | Mensajería | Redis (cola) |
| busqueda | Descubrimiento | OpenSearch |

## Comunicación entre servicios

Los servicios se comunican por HTTP a través de la pasarela interna. Los eventos asíncronos (pedido creado, usuario registrado) viajan por la cola de notificaciones. Ningún servicio accede directamente a la base de datos de otro.

## Entornos

Hay tres entornos: desarrollo, pruebas y producción. Solo producción tiene alertas que despiertan a la persona de guardia.

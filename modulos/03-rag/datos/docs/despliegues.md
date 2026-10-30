# Política de despliegues

Todos los despliegues a producción pasan por la canalización de integración continua.

## Ventanas

No se despliega a producción los viernes después de las 15:00 ni en vísperas de festivo, salvo correcciones de incidentes críticos aprobadas por el responsable del equipo.

## Despliegue gradual

Los cambios se despliegan primero en un canario que recibe el 10 % del tráfico durante 30 minutos. Si las métricas del canario empeoran, el despliegue se detiene solo.

## Migraciones de base de datos

Una migración que borra columnas o tablas necesita la aprobación de dos personas del equipo y una copia de seguridad verificada justo antes del despliegue. Esta regla se añadió tras el incidente de usuarios de julio de 2026.

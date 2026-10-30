# Postmortem: pérdida de teléfonos de usuarios (julio de 2026)

## Resumen

El 3 de julio de 2026, una migración del servicio de usuarios borró la columna telefono. Se perdieron los teléfonos de todos los usuarios.

## Recuperación

Los datos se recuperaron de la copia de seguridad de la noche anterior. La restauración tardó 4 horas. Los teléfonos que los usuarios cambiaron ese día se perdieron.

## Causa raíz

La migración se escribió para renombrar la columna, pero el script borraba la antigua antes de copiar los datos. Nadie la revisó porque las migraciones no necesitaban aprobación.

## Acciones

Desde este incidente, las migraciones que borran columnas o tablas necesitan la aprobación de dos personas y una copia de seguridad verificada antes del despliegue.

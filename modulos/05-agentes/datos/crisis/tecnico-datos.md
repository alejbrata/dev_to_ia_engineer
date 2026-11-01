# Runbook: datos expuestos en el almacenamiento

Usa este runbook cuando un fichero o un contenedor de almacenamiento con datos de clientes sea accesible sin autenticación.

## Mitigación

1. Retira el acceso público al contenedor de inmediato.
2. Rota las credenciales que pudieran estar en los ficheros expuestos o tuvieran acceso al contenedor.
3. Conserva los logs de acceso del contenedor como evidencia: los necesitará el equipo legal para saber qué datos se descargaron y cuándo.

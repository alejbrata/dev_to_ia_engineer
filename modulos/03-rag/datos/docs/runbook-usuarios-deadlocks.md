# Runbook: deadlocks en la base de datos de usuarios

Usa este runbook cuando aparezca deadlock detected en los logs del servicio de usuarios.

## Diagnóstico

Los deadlocks en usuarios casi siempre vienen de dos operaciones que actualizan el perfil y la tabla de sesiones en distinto orden. Busca en los logs qué dos consultas aparecen juntas en el error.

## Mitigación

PostgreSQL resuelve el deadlock cancelando una de las transacciones, así que el usuario ve un error y puede reintentar. Si los deadlocks son continuos, desactiva temporalmente la edición de perfil con el interruptor de funcionalidad perfil_edicion y abre una incidencia al equipo Identidad.

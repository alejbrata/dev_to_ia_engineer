# Runbook: los emails no salen

Usa este runbook cuando el servicio de notificaciones no pueda enviar emails.

## Diagnóstico

1. Busca en los logs Connection timed out hacia el servidor SMTP.
2. Comprueba que el puerto 587 está abierto desde los pods de notificaciones hacia el servidor SMTP. Los cambios de firewall son la causa más habitual.
3. Mira la cola de Redis: si los emails no salen, se acumulan.

## Mitigación

Si el puerto está cerrado por un cambio de firewall, pide al equipo de redes que lo vuelva a abrir. Mientras tanto, los emails quedan en la cola y se envían cuando se restablece la conexión, siempre que la cola no se llene.

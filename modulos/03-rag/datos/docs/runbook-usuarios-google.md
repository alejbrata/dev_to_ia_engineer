# Runbook: errores en el inicio de sesión con Google

Usa este runbook cuando el inicio de sesión con Google falle con el error invalid_grant.

## Causa habitual

El error invalid_grant suele aparecer cuando el secreto de cliente de OAuth ha caducado o se ha rotado sin actualizar la configuración del servicio de usuarios. También puede deberse a que el reloj del servidor esté desincronizado más de cinco minutos.

## Solución

1. Comprueba la fecha de caducidad del secreto de cliente en la consola de Google.
2. Si ha caducado, genera uno nuevo y guárdalo en el gestor de secretos, en la ruta usuarios/google/secreto.
3. Comprueba la hora de los servidores con el equipo de plataforma.

El inicio de sesión con usuario y contraseña no se ve afectado, así que no es un incidente crítico mientras funcione.

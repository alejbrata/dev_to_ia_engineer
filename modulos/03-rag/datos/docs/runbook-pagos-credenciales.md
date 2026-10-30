# Runbook: credenciales de pagos

El token de la API del banco caduca cada 90 días. Si caduca, pagos rechaza todos los cobros con un error 401.

## Renovación

1. Pide un token nuevo en el portal del banco con la cuenta de servicio del equipo Cobros.
2. Guárdalo en el gestor de secretos, en la ruta pagos/banco/token.
3. Reinicia los pods de pagos para que lean el secreto nuevo.

## Prevención

El gestor de secretos avisa 14 días antes de la caducidad. Ese aviso llega al canal del equipo Cobros, no a la persona de guardia.

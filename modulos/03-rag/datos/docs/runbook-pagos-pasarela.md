# Runbook: errores con la pasarela de pago

Usa este runbook cuando las llamadas de pagos a la pasarela externa fallen con connection reset by peer o con timeouts.

## Diagnóstico

1. Consulta la página de estado del proveedor de la pasarela.
2. Mira el porcentaje de errores en el panel de pagos. Por debajo del 5 % suele ser ruido de red; por encima, es un incidente.
3. Comprueba que el certificado TLS de la pasarela no ha cambiado.

## Mitigación

El conector ya reintenta tres veces con backoff exponencial. No aumentes los reintentos: si la pasarela está saturada, más reintentos la saturan más. Si el problema es del proveedor, abre una incidencia con ellos y avisa al equipo de atención al cliente.

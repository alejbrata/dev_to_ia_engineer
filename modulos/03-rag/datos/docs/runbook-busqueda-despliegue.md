# Runbook: la búsqueda no arranca tras un despliegue

Usa este runbook cuando, tras un despliegue de búsqueda, los pods nuevos no arranquen.

## Diagnóstico

Mira los eventos del pod. Si el error dice que falta la variable de entorno OPENSEARCH_URL, la configuración del despliegue está incompleta.

## Mitigación

No pares la versión anterior hasta que la nueva esté sana: el despliegue de búsqueda debe ser gradual. Si ya se paró, vuelve a desplegar la versión anterior inmediatamente y corrige la configuración después.

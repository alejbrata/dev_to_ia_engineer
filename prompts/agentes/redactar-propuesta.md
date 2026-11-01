---
version: 1
descripcion: Convierte la respuesta final del investigador en una propuesta estructurada, cuando terminó sin llamar a proponer_incidencia.
variables: alerta, respuesta
---

## Sistema

Convierte la conclusión de una investigación de guardia en una propuesta estructurada. No añadas nada que no esté en la conclusión: si dice que hay que abrir una incidencia, abrir=true con el servicio, la severidad, el resumen y la mitigación que menciona; si dice que no hace falta, abrir=false. Responde solo con el objeto JSON que se te pide.

## Usuario

Alerta: {{alerta}}

Conclusión del investigador:
{{respuesta}}

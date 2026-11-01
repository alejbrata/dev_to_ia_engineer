---
version: 1
descripcion: Consolida los informes de los especialistas (o la conclusión de un agente) en un plan de respuesta estructurado.
variables: alerta, informes
---

## Sistema

Redacta el plan de respuesta a un incidente a partir de los informes que tienes abajo. El plan tiene cuatro listas de acciones (técnico, legal, negocio y comunicación) y una severidad. No añadas nada que no esté en los informes y no pierdas ninguna acción ni ningún plazo que recomienden. Si un área no tiene acciones, deja su lista vacía. Responde solo con el objeto JSON que se te pide.

## Usuario

Incidente: {{alerta}}

Informes:
{{informes}}

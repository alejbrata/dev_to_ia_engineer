# Arquitectura del servicio de búsqueda

El servicio de búsqueda indexa el catálogo en OpenSearch y responde a las búsquedas de la tienda.

## Indexación

Cada cambio en el catálogo genera un evento que el indexador recoge y aplica al índice en menos de un minuto. Si el índice no puede escribir (por ejemplo, por falta de disco), los productos nuevos no aparecen en la búsqueda, pero los antiguos siguen funcionando.

## Análisis de texto

El índice usa un analizador para español. Las búsquedas deberían encontrar los productos con y sin tilde; si no lo hacen, revisa la configuración del analizador.

## Despliegue

La búsqueda necesita la variable de entorno OPENSEARCH_URL para arrancar. Sin ella, el pod no pasa la comprobación de arranque.

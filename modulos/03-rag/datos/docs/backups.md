# Copias de seguridad

Las bases de datos PostgreSQL de pagos, usuarios y catálogo tienen copia de seguridad completa cada noche a las 02:00.

## Retención

Las copias diarias se guardan 30 días. Las del primer día de cada mes se guardan un año.

## Pruebas de restauración

Una vez al mes, el equipo de plataforma restaura una copia en un entorno aislado para comprobar que funciona. Una copia que nunca se ha restaurado no se considera una copia válida.

## Redis y OpenSearch

La cola de Redis no tiene copia de seguridad: los mensajes son temporales. El índice de OpenSearch tampoco: se puede reconstruir desde el catálogo en unas 6 horas.

# Arquitectura del servicio de usuarios

El servicio de usuarios gestiona el registro, el inicio de sesión y los perfiles.

## Inicio de sesión

Hay dos formas de iniciar sesión: usuario y contraseña, y Google mediante OAuth. Las sesiones se guardan como tokens firmados con una validez de 12 horas.

## Datos

Los perfiles se guardan en PostgreSQL. Las migraciones de esquema se ejecutan durante el despliegue, antes de arrancar la nueva versión.

## Dependencias

El servicio de usuarios no depende de ningún otro servicio para el inicio de sesión con contraseña. El inicio de sesión con Google depende del proveedor externo de Google.

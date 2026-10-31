# Publicar la web en un VPS con dominio propio

La web se sigue publicando en GitHub Pages (`.github/workflows/deploy.yml`). Esta guía añade una segunda copia en un servidor propio con tu dominio y HTTPS. Las dos se construyen desde el mismo código: solo cambian `SITIO_URL` y `SITIO_BASE` al construir (ver `site/astro.config.mjs`).

La web es estática: el servidor solo tiene que servir la carpeta `site/dist`. No hace falta Node.js ni nada del curso en el VPS.

## Qué necesitas

- Un VPS con Linux (Debian o Ubuntu en esta guía) y acceso por SSH.
- Un dominio o subdominio (por ejemplo, `curso.midominio.es`).
- En tu equipo: Node.js (ya lo usas para la web) y `rsync`. En Windows, `rsync` viene con WSL; con Git Bash solo, usa el flujo de GitHub Actions del paso 6.

## 1. DNS

En el panel de tu proveedor de dominio, crea un registro `A` (y `AAAA` si el VPS tiene IPv6) de `curso.midominio.es` a la IP del VPS. Comprueba que resuelve antes de seguir:

```sh
dig +short curso.midominio.es
```

Caddy necesita que el dominio apunte ya al servidor para conseguir el certificado.

## 2. Un usuario para desplegar

En el VPS, crea un usuario sin privilegios que solo pueda escribir en la carpeta de la web:

```sh
sudo adduser --disabled-password despliegue
sudo mkdir -p /var/www/curso
sudo chown despliegue:despliegue /var/www/curso
sudo apt install rsync
```

En tu equipo, genera una clave solo para desplegar y copia la parte pública al VPS:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/id_despliegue -C despliegue-curso
ssh-copy-id -i ~/.ssh/id_despliegue.pub despliegue@curso.midominio.es
```

## 3. Cortafuegos

Abre solo SSH, HTTP (80, lo usa Caddy para el certificado y para redirigir a HTTPS) y HTTPS (443). Con `ufw`:

```sh
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable
```

## 4. Caddy

Instala Caddy siguiendo su [guía oficial para Debian y Ubuntu](https://caddyserver.com/docs/install#debian-ubuntu-raspbian). Después, copia `deploy/Caddyfile` a `/etc/caddy/Caddyfile` en el VPS, cambia `curso.midominio.es` por tu dominio y recarga:

```sh
sudo systemctl reload caddy
```

Caddy obtiene y renueva el certificado HTTPS solo.

## 5. Publicar desde tu equipo

Desde la raíz del repo:

```sh
SITIO_URL=https://curso.midominio.es VPS=despliegue@curso.midominio.es ./deploy/publicar.sh
```

El script construye la web con la raíz `/` y la sube con `rsync --delete`: lo que ya no existe en el build se borra del servidor. Abre `https://curso.midominio.es` para comprobarlo.

Si usas Git Bash en Windows, `publicar.sh` ya pone `MSYS_NO_PATHCONV=1`: sin eso, Git Bash convierte `SITIO_BASE=/` en `C:/Program Files/Git/` y todas las rutas de la web salen rotas.

## 6. Publicar desde GitHub Actions (opcional)

`.github/workflows/deploy-vps.yml` hace lo mismo desde GitHub, a mano (Actions → Despliegue en VPS → Run workflow). Necesita, en Settings → Secrets and variables → Actions:

| Tipo | Nombre | Valor |
| --- | --- | --- |
| Secreto | `VPS_HOST` | `curso.midominio.es` o la IP |
| Secreto | `VPS_USUARIO` | `despliegue` |
| Secreto | `VPS_CLAVE_SSH` | el contenido de `~/.ssh/id_despliegue` (la privada) |
| Secreto | `VPS_KNOWN_HOSTS` | la salida de `ssh-keyscan curso.midominio.es` |
| Variable | `SITIO_URL` | `https://curso.midominio.es` |

`VPS_KNOWN_HOSTS` hace que la conexión falle si alguien suplanta al servidor, en lugar de aceptar cualquier clave. Si quieres que se publique en cada push a `main`, como GitHub Pages, añade el disparador `push` al flujo.

## Comprobaciones

- `curl -I https://curso.midominio.es` devuelve `200` y una cabecera `server: Caddy`.
- `curl -I https://curso.midominio.es/no-existe/` devuelve `404` con la página de error de la web.
- Los enlaces entre lecciones funcionan: son relativos, así que no dependen de la raíz.

## Estado

Revisado: 2026-10. El build con `SITIO_BASE=/` se ha comprobado en local (rutas en la raíz y URL canónica con el dominio). El despliegue en un VPS real no se ha probado todavía: falta un servidor y un dominio.

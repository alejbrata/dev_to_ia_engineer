#!/usr/bin/env bash
# Construye la web para un dominio propio y la sube al VPS con rsync.
#
# Uso (desde la raíz del repo):
#   SITIO_URL=https://curso.midominio.es VPS=usuario@ip-o-host ./deploy/publicar.sh
#
# Necesita Node.js, rsync y acceso por SSH con clave al VPS (deploy/README.md).
set -euo pipefail

: "${SITIO_URL:?Falta SITIO_URL, por ejemplo https://curso.midominio.es}"
: "${VPS:?Falta VPS, por ejemplo despliegue@203.0.113.10}"
DESTINO="${DESTINO:-/var/www/curso}"

cd "$(dirname "$0")/../site"
npm ci
# MSYS_NO_PATHCONV: en Git Bash de Windows, evita que "/" se convierta en "C:/Program Files/Git/".
MSYS_NO_PATHCONV=1 SITIO_URL="$SITIO_URL" SITIO_BASE=/ npm run build

# --delete borra del servidor lo que ya no existe en dist/: el VPS queda igual que el build.
rsync -az --delete dist/ "$VPS:$DESTINO/"
echo "Publicado en $SITIO_URL"

#!/usr/bin/env bash
# Se ejecuta una vez, al crear el contenedor: uv, las dependencias del curso, Ollama y los
# modelos de los roles `chat` y `embeddings` (los nombres salen de config/models.toml).
set -euo pipefail

# Si la carpeta viene montada desde otro sistema (un contenedor local en Windows o macOS), git
# no la reconoce como propia y se niega a trabajar en ella. En Codespaces no hace falta.
git config --global --add safe.directory "$PWD"

echo "== uv y las dependencias del curso"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync

echo "== .env (si no existe, una copia de .env.example sin claves)"
[ -f .env ] || cp .env.example .env

echo "== Ollama"
if ! command -v ollama >/dev/null; then
	# El instalador descomprime con zstd, que la imagen base no trae. El update puede avisar de
	# un repositorio de la imagen con la clave caducada (el de Yarn): no impide instalar zstd.
	sudo apt-get update -qq || true
	sudo apt-get install -y -qq zstd
	curl -fsSL https://ollama.com/install.sh | sh
fi
bash .devcontainer/arrancar.sh

echo "== Modelos de los roles chat y embeddings"
modelos=$(uv run python -c "
import tomllib
c = tomllib.load(open('config/models.toml', 'rb'))
print(' '.join(c['roles'][r]['model'] for r in ('chat', 'embeddings')))
")
for modelo in $modelos; do
	ollama pull "$modelo"
done

echo "== Listo. Comprueba el entorno con:"
echo "   uv run python modulos/00-introduccion/comprobar_entorno.py"

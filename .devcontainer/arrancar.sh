#!/usr/bin/env bash
# Se ejecuta cada vez que arranca el contenedor: deja Ollama sirviendo en segundo plano.
set -uo pipefail

if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
	nohup ollama serve >/tmp/ollama.log 2>&1 &
	for _ in $(seq 1 30); do
		curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
		sleep 1
	done
fi
curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && echo "Ollama en marcha" \
	|| echo "Ollama no arrancó: mira /tmp/ollama.log"

#!/usr/bin/env bash
# Wrapper de retrocompatibilidad para Docker Compose.
# Detecta si la maquina tiene el plugin nuevo ("docker compose") o el
# binario antiguo ("docker-compose") y reenvia los argumentos al que exista.
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
	exec docker compose "$@"
elif command -v docker-compose >/dev/null 2>&1; then
	exec docker-compose "$@"
else
	echo "Error: no se encontro 'docker compose' (plugin) ni 'docker-compose' (binario) instalado." >&2
	exit 1
fi

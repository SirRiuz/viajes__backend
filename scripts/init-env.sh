#!/usr/bin/env bash
# Crea .env a partir de .env.template (solo si no existe), con SECRET_KEY y
# API_SECRET_KEY aleatorias y el usuario actual como APP_UID/APP_GID. Es el
# unico archivo de entorno: lo leen igual el stack de desarrollo y el de
# produccion.
set -euo pipefail

if [ -f .env ]; then
	exit 0
fi

random_key() {
	head -c 64 /dev/urandom | base64 | tr -d '/+=\n' | head -c "$1"
}

sed \
	-e "s|^SECRET_KEY = \"...\"|SECRET_KEY = \"$(random_key 64)\"|" \
	-e "s|^API_SECRET_KEY = \"...\"|API_SECRET_KEY = \"$(random_key 48)\"|" \
	-e "s|^APP_UID = .*|APP_UID = $(id -u)|" \
	-e "s|^APP_GID = .*|APP_GID = $(id -g)|" \
	.env.template > .env

echo "Creado .env desde .env.template (revisalo antes de desplegar)."

DC := scripts/docker-compose.sh
# Production stack (Granian + nginx + valkey). Dev and prod read the same .env.
PROD := $(DC) -p viajes -f ci/docker-compose.yml --env-file .env

# Primer uso: crea .env desde .env.template con claves aleatorias
.env:
	scripts/init-env.sh

# Dev y prod usan los mismos puertos: arrancar uno detiene el otro. `stop`
# (no `down`) conserva sus contenedores y datos para volver despues.
build: .env
	$(DC) build

# media/ la crea el usuario (no root, como haria Docker al montarla en nginx)
up: .env
	-@$(PROD) stop 2>/dev/null
	@mkdir -p media
	$(DC) up

run: up

stop:
	$(DC) stop

# Las migraciones se aplican automaticamente en `make up`/`make run`
# (servicio "migration" en docker-compose.yml, web espera a que termine).
# Este target es un atajo manual para cuando el stack ya esta arriba
# y solo quieres aplicar migraciones nuevas sin reiniciar todo.
migrate: .env
	$(DC) up migration --build

dependencies:
	$(DC) run --rm --no-deps web sh -c "pip-compile --no-emit-index-url requirements.in"

test: .env
	$(DC) run --rm web py.test --no-migrations

test-html-cov-report:
	$(DC) run --rm web py.test --no-migrations --cov=. --cov-report=html

shell:
	$(DC) run --rm web python manage.py shell

bash:
	$(DC) run --rm web bash

startapp:
	@$(eval APP_NAME := $(word 2,$(MAKECMDGOALS)))
	$(DC) run --rm web python manage.py startapp $(APP_NAME)

# --no-deps: makemigrations solo lee modelos y archivos en disco, no toca la
# DB. Sin esto, arrancar "web" arrastraria al servicio "migration" (que
# necesita migraciones ya generadas para poder aplicarlas) creando un
# huevo-y-gallina en un clone nuevo, ya que las migraciones no van en git.
migrations: .env
	$(DC) run --rm --no-deps web python manage.py makemigrations

createsuperuser:
	$(DC) run --rm web python manage.py createsuperuser

check:
	$(DC) run --rm web python manage.py check

# --- Produccion (ci/docker-compose.yml) -------------------------------------
# `make prod-up` genera y aplica las migraciones (servicio "migration") y,
# en el primer despliegue tras el refactor, adopta las tablas existentes.
# `make prod-migrations` solo las genera, para revisarlas antes.
# En una maquina de desarrollo funciona igual, con el mismo .env: `make
# prod-up` y `make up` alternan entre los dos modos.
prod-build:
	$(PROD) build

prod-up: .env
	-@$(DC) stop 2>/dev/null
	@mkdir -p media
	$(PROD) up -d --build

prod-stop:
	$(PROD) stop

prod-down:
	$(PROD) down

prod-logs:
	$(PROD) logs -f --tail=200

prod-migrations:
	$(PROD) run --rm --no-deps web python manage.py makemigrations

prod-migrate:
	$(PROD) up migration --build

prod-check:
	$(PROD) run --rm --no-deps web python manage.py check --deploy

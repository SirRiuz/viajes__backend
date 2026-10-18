# Viajes backend

Django 6.1 + GraphQL (graphene) on Python 3.15. Same layout as afrodita:

```
viajes/      project: settings, urls, GraphQL schema, wsgi/asgi
app/         the application: models, schemas (queries/mutations), types,
             rest (healthcheck, driver documents), utils, middlewares, tests
honeypot/    fake /admin/ that blacklists bots
constants/   messages and choices
nginx/       nginx.conf.template (rate limits, Cloudflare real IP)
ci/          production docker-compose (Granian)
scripts/     docker compose wrapper
```

### Running the project in development environment

1. `cp .env.template .env` and fill it in
2. `make build`: builds docker containers
3. `make migrations`: generates migrations (they are not in git)
4. `make up`: applies migrations and starts the dev server (nginx on `SERVER_PORT`)
5. `make createsuperuser`: creates admin user (`/staff/tools/`)

`make test` runs the suite, `make check`, `make shell`, `make bash` as usual.

### Production

`ci/docker-compose.yml`: Granian (Rust HTTP server, WSGI; 2 workers × 4
threads, `GRANIAN_*` in the Dockerfile) behind nginx, Valkey as shared cache.
Same `.env`; `DEBUG` is forced off, so GraphiQL (`/graphiql/`), Swagger and
introspection don't exist there. They work locally with `DEBUG = True`.

1. `make prod-migrations`
2. `make prod-up` (the `migration` service runs before `web`)

`make prod-logs`, `make prod-down`, `make prod-check` (`check --deploy`).

#### Dev and prod on the same machine

There is a single `.env`, read the same by both stacks. They use the same
ports, so they alternate: `make up` stops the prod stack first and `make
prod-up` stops the dev one (`stop`, so both keep their containers and data).
The prod stack forces `DEBUG` off; `ALLOWED_HOSTS` must list real hosts
(`localhost,127.0.0.1` on a dev machine, the domain on the server).

With `COMPOSE_PROFILES = "local-db"` both stacks run the local PostgreSQL on
the same volume (same data in both modes); without it they use the
database in `.env` (e.g. Neon).

#### First deploy after the move to the afrodita layout

The tables keep their names, nothing is copied. Before `migrate`, the
`migration` service runs `adopt_legacy_schema`, which moves Django's
bookkeeping (content types, permissions, migration history) from the old
`users`, `driver`, `route`, `vessel`, `trip`, `tickets` apps to `app`. It
does nothing on a fresh or already adopted database. Steps:

1. Back up the database.
2. In `.env`: `SECRET_KEY` of 50+ characters and `ALLOWED_HOSTS` with the
   real hosts (production refuses to start otherwise). A new `SECRET_KEY`
   signs users out once.
3. `APP_UID`/`APP_GID` = `id -u`/`id -g` of the folder owner (the
   containers no longer run as root).
4. `make prod-migrations && make prod-up`.

#### Hiding the server behind Cloudflare

nginx answers only Cloudflare (and this machine): any other connection is
closed without a reply, so scanners can't tie the server's IP to the site.
Recommended on the server: a Cloudflare Tunnel (`COMPOSE_PROFILES` with
`tunnel`, `TUNNEL_TOKEN`, `NGINX_BIND = "127.0.0.1"`), so no port is open at
all. Details and the steps outside the code (new server IP, DNS records) in
`SECURITY.md`.

See `SECURITY.md` for the security and performance changes.

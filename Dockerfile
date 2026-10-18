# --- Build: compiles the C extensions (psycopg) into a virtualenv ------------
FROM python:3.15.0-slim-trixie AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r /tmp/requirements.txt pip-tools

# --- Runtime: slim image, no compilers, non-root -----------------------------
FROM python:3.15.0-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY --chown=app:app . /app

USER app

EXPOSE 8080

# Production server: Granian (Rust HTTP server, WSGI interface). Every option
# can be overridden with its GRANIAN_* variable (compose / .env). Sized for a
# small machine: few processes, each with threads, since requests mostly wait
# on the database. docker-compose's `web` overrides it with runserver locally.
# - BACKPRESSURE: at most this many requests in flight per worker; beyond it
#   Granian answers 503 at once instead of piling up a queue (nginx limits first)
# - WORKERS_LIFETIME / WORKERS_MAX_RSS: workers are replaced now and then, and
#   before they outgrow the RAM
ENV GRANIAN_INTERFACE=wsgi \
    GRANIAN_HOST=0.0.0.0 \
    GRANIAN_PORT=8080 \
    GRANIAN_HTTP=1 \
    GRANIAN_WEBSOCKETS=false \
    GRANIAN_WORKERS=2 \
    GRANIAN_BLOCKING_THREADS=4 \
    GRANIAN_BACKPRESSURE=32 \
    GRANIAN_RESPAWN_FAILED_WORKERS=true \
    GRANIAN_WORKERS_LIFETIME=6h \
    GRANIAN_WORKERS_MAX_RSS=320 \
    GRANIAN_WORKERS_KILL_TIMEOUT=20s \
    GRANIAN_LOG_LEVEL=warning \
    GRANIAN_LOG_ACCESS_ENABLED=false

CMD ["granian", "viajes.wsgi:application"]

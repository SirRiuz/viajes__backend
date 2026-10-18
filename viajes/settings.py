"""
Django settings for viajes project.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

# Python
import os
import sys
from pathlib import Path

# Libs
from decouple import config
from django.core.exceptions import ImproperlyConfigured

from constants.exceptions import ErrorMessages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

TESTING = "pytest" in sys.modules


def csv(value: str) -> list:
    """Comma-separated setting; an unset or empty variable is an empty list."""
    return [item.strip() for item in value.split(",") if item.strip()]


# SECURITY WARNING: don't run with debug turned on in production!
# Off unless asked for: a missing variable must never expose debug pages
DEBUG = config("DEBUG", default=False, cast=bool)
STAGE = config("STAGE", default="DEVELOP")

SHORT_ID_SIZE = 6
PAGINATION_PAGE_SIZE = 15

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=csv)
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=csv)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")
API_SECRET_KEY = config("API_SECRET_KEY")

# SECRET_KEY also signs the session tokens (JWT, HS256): a short key can be
# brute-forced offline from one captured token, and then anyone could mint a
# session for any account. Production refuses to start with one, and with
# ALLOWED_HOSTS «*» (Host header injection).
if not DEBUG and not TESTING:
    if len(SECRET_KEY) < 50:
        raise ImproperlyConfigured(ErrorMessages.SECRET_KEY_TOO_SHORT)
    if "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured(ErrorMessages.ALLOWED_HOSTS_WILDCARD)

ENCRYPTED_RESPONSE = config("ENCRYPTED_RESPONSE", default=False, cast=bool)
SINGLE_REQUEST_PROTECT = config("SINGLE_REQUEST_PROTECT", default=False, cast=bool)

# How many reverse proxies append to X-Forwarded-For before Django (nginx =
# 1; Cloudflare's address is replaced by the visitor's in nginx/real_ip.conf).
# Rate limits and the honeypot blacklist key on this address.
TRUSTED_PROXY_COUNT = config("TRUSTED_PROXY_COUNT", default=1, cast=int)

# Paths of the admin and the GraphQL endpoint. The frontend calls /graphql/;
# a less obvious admin path keeps bots away from its log-in.
INTERNAL_ADMIN_URL = config("INTERNAL_ADMIN_URL", default="staff/tools/")
INTERNAL_GRAPHQL_URL = config("INTERNAL_GRAPHQL_URL", default="graphql/")

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=csv)

# Application definition
PROJECT_APPS = [
    "app",
    "honeypot",
]

EXTERNAL_APPS = [
    "corsheaders",
    "storages",
    "graphene_django",
    "django_cleanup.apps.CleanupConfig",
]
# Swagger UI, a debugging tool: only routed with DEBUG (viajes/urls.py)
if DEBUG:
    EXTERNAL_APPS.append("drf_yasg")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
]

INSTALLED_APPS = DJANGO_APPS + EXTERNAL_APPS + PROJECT_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    # Admin log-in attempts per address (before the session is even loaded)
    "app.middlewares.admin_throttle.AdminLoginThrottleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "honeypot.middleware.HoneyPotMiddleware",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
ROOT_URLCONF = "viajes.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "viajes.wsgi.application"

# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASE_CONNECTION_CONFIG = {}
DATABASE_ENGINE = config("DATABASE_ENGINE", default="django.db.backends.sqlite3")

if "sqlite3" not in DATABASE_ENGINE:
    DATABASE_CONNECTION_CONFIG = {
        "USER": config("DATABASE_USER"),
        "HOST": config("DATABASE_HOST"),
        "PORT": config("DATABASE_PORT"),
        "PASSWORD": config("DATABASE_PASSWORD"),
    }

DATABASES = {
    "default": {
        "ENGINE": DATABASE_ENGINE,
        "NAME": config("DATABASE_NAME", default="test.sqlite3"),
        **DATABASE_CONNECTION_CONFIG,
        # Reuse the connection between requests (a new PostgreSQL connection
        # costs several ms and a process on the server); checked before use
        "CONN_MAX_AGE": config("DATABASE_CONN_MAX_AGE", default=60, cast=int),
        "CONN_HEALTH_CHECKS": True,
    }
}
if "sqlite3" in DATABASE_ENGINE:
    DATABASES["default"]["OPTIONS"] = {
        # Several Granian workers share the file: WAL lets readers work
        # while one writes, IMMEDIATE takes the write lock up front (no
        # «database is locked» half-way through a transaction) and a writer
        # waits up to 20 s for its turn instead of failing.
        "init_command": (
            "PRAGMA journal_mode=WAL;"
            "PRAGMA synchronous=NORMAL;"
            "PRAGMA temp_store=MEMORY;"
            "PRAGMA mmap_size=134217728;"
            "PRAGMA cache_size=-16000;"
        ),
        "transaction_mode": "IMMEDIATE",
        "timeout": 20,
    }
else:
    DATABASES["default"]["OPTIONS"] = {
        "sslmode": config("DATABASE_SSLMODE", default="require"),
        "connect_timeout": 5,
        # A runaway query is cut at 10 s instead of holding a worker (the
        # migration service sets 0: no limit)
        "options": f"-c statement_timeout={config('DATABASE_STATEMENT_TIMEOUT_MS', default=10000, cast=int)}",
    }

# Shared cache: rate limits, the honeypot blacklist and the replay
# protection must be the same for every worker. Valkey (docker-compose
# `valkey`); per-process memory when CACHE_URL is empty (tests, local).
CACHE_URL = config("CACHE_URL", default="")
if CACHE_URL and not TESTING:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_URL,
            "KEY_PREFIX": "vj",
            "TIMEOUT": 300,
            "OPTIONS": {"socket_connect_timeout": 2, "socket_timeout": 2},
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

AUTHENTICATION_BACKENDS = [
    "graphql_jwt.backends.JSONWebTokenBackend",
    "django.contrib.auth.backends.ModelBackend",
]

REST_FRAMEWORK = {
    "PAGE_SIZE": 15,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_RENDERER_CLASSES": [
        ("app.renders.encoder.EncodeRenderer" if ENCRYPTED_RESPONSE else "rest_framework.renderers.JSONRenderer"),
    ],
    # OPTIONS answered empty: DRF's metadata («renders», «parses») names it
    "DEFAULT_METADATA_CLASS": None,
    "EXCEPTION_HANDLER": "app.rest.exceptions.exception_handler_without_signature",
}

GRAPHENE = {
    "SCHEMA": "viajes.schema.schema",
    "MIDDLEWARE": [
        # graphql_jwt's JSONWebTokenMiddleware, on root fields only
        "app.middlewares.graphql_jwt.RootJSONWebTokenMiddleware",
    ],
}

# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Bogota"

USE_I18N = True

USE_TZ = True

# AWS Storage Configuration
# Driver documents live in the S3 bucket. Off: local disk (MEDIA_ROOT).
USE_AWS_STORAGE_SYSTEM = config("USE_AWS_STORAGE_SYSTEM", default=True, cast=bool)

if USE_AWS_STORAGE_SYSTEM:
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL")
    AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN")

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- HTTP hardening ---------------------------------------------------------
# GraphQL bodies are a few KB: refuse big ones before reading them. Files
# (driver documents) are not counted here; nginx caps their size.
DATA_UPLOAD_MAX_MEMORY_SIZE = config("DATA_UPLOAD_MAX_MEMORY_SIZE", default=1024 * 1024, cast=int)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# --- No framework fingerprints ----------------------------------------------
# «sessionid», «csrftoken» and «messages» are Django's cookie names, the first
# thing fingerprinting tools (Wappalyzer, WhatWeb) look for. Error pages and
# CSRF failures are plain too (app/views/errors.py, handlers in urls.py).
SESSION_COOKIE_NAME = "sid"
CSRF_COOKIE_NAME = "xsrf"
MESSAGE_STORAGE = "app.utils.messages.FlashCookieStorage"
CSRF_FAILURE_VIEW = "app.views.errors.csrf_failure"
# Admin sessions: 8 hours, gone when the browser closes
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HTTPS only, for a year, once the site serves TLS (set by the proxy)
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}

AUTH_USER_MODEL = "app.User"

# Default primary key field type
# https://docs.djangoproject.com/en/6.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

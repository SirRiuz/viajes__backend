"""Branches of viajes/settings.py that depend on the environment."""

import importlib
import os
import runpy
import sys
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

import viajes

SETTINGS = Path(viajes.__file__).with_name("settings.py")
BASE_ENV = {
    "DEBUG": "True",
    "SECRET_KEY": "s" * 60,
    "API_SECRET_KEY": "a" * 40,
    "ALLOWED_HOSTS": "api.example.com",
    "DATABASE_ENGINE": "django.db.backends.sqlite3",
    "USE_AWS_STORAGE_SYSTEM": "False",
    "CACHE_URL": "",
}


def load(production=False, **env):
    """Runs settings.py with `env`; `production` hides pytest from it."""
    with mock.patch.dict(os.environ, {**BASE_ENV, **env}), mock.patch.dict(sys.modules):
        if production:
            sys.modules.pop("pytest", None)
        return runpy.run_path(str(SETTINGS))


class SettingsTestCase(SimpleTestCase):
    def test_production_refuses_a_short_secret_key(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "at least 50"):
            load(production=True, DEBUG="False", SECRET_KEY="short")

    def test_production_refuses_wildcard_hosts(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "real hosts"):
            load(production=True, DEBUG="False", ALLOWED_HOSTS="*")

    def test_lists_ignore_empty_entries(self):
        values = load(ALLOWED_HOSTS="a.com, ,b.com,", CORS_ALLOWED_ORIGINS="")
        self.assertEqual((values["ALLOWED_HOSTS"], values["CORS_ALLOWED_ORIGINS"]), (["a.com", "b.com"], []))

    def test_swagger_app_only_while_debugging(self):
        self.assertIn("drf_yasg", load()["INSTALLED_APPS"])

    def test_production_hardening(self):
        values = load(production=True, DEBUG="False", CACHE_URL="redis://valkey:6379/0")
        self.assertNotIn("drf_yasg", values["INSTALLED_APPS"])
        self.assertTrue(values["SESSION_COOKIE_SECURE"])
        self.assertEqual(values["SECURE_HSTS_SECONDS"], 31536000)
        self.assertEqual(values["CACHES"]["default"]["BACKEND"], "django.core.cache.backends.redis.RedisCache")

    def test_tests_use_local_memory_cache(self):
        values = load(CACHE_URL="redis://valkey:6379/0")
        self.assertEqual(values["CACHES"]["default"]["BACKEND"], "django.core.cache.backends.locmem.LocMemCache")

    def test_sqlite_tuning(self):
        options = load()["DATABASES"]["default"]["OPTIONS"]
        self.assertIn("journal_mode=WAL", options["init_command"])
        self.assertEqual(options["transaction_mode"], "IMMEDIATE")

    def test_postgresql_options(self):
        values = load(
            DATABASE_ENGINE="django.db.backends.postgresql",
            DATABASE_USER="u",
            DATABASE_HOST="h",
            DATABASE_PORT="5432",
            DATABASE_PASSWORD="p",
            DATABASE_SSLMODE="verify-full",
        )
        options = values["DATABASES"]["default"]["OPTIONS"]
        self.assertEqual(options["sslmode"], "verify-full")
        self.assertEqual(options["options"], "-c statement_timeout=10000")

    def test_s3_storage(self):
        values = load(
            USE_AWS_STORAGE_SYSTEM="True",
            AWS_ACCESS_KEY_ID="k",
            AWS_SECRET_ACCESS_KEY="s",
            AWS_STORAGE_BUCKET_NAME="b",
            AWS_S3_ENDPOINT_URL="https://s3.example.com",
            AWS_S3_CUSTOM_DOMAIN="cdn.example.com",
        )
        self.assertEqual(values["STORAGES"]["default"]["BACKEND"], "storages.backends.s3boto3.S3Boto3Storage")

    def test_wsgi_and_asgi_entry_points(self):
        self.assertTrue(callable(importlib.import_module("viajes.wsgi").application))
        self.assertTrue(callable(importlib.import_module("viajes.asgi").application))

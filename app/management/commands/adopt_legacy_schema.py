"""
One-time switch of an existing database from the old per-app layout
(apps/users, apps/driver, apps/route, apps/vessel, apps/trip, apps/tickets)
to the single `app` application.

The tables are not touched: the models keep their old names (Meta.db_table).
Only Django's own bookkeeping moves:

- django_content_type: users.user → app.user, driver.driver → app.driver…
  so admin permissions, groups and the admin log keep pointing at them.
- django_migrations: the old labels' rows are dropped and app's freshly
  generated migrations are recorded as applied (their tables already exist).

Runs before every `migrate` (docker-compose `migration` service) and does
nothing on a fresh database or one already adopted.
"""

# Django
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

# Constants
from constants.exceptions import ErrorMessages

APP_LABEL = "app"
LEGACY_MODELS = {
    "users": "user",
    "driver": "driver",
    "route": "route",
    "vessel": "vessel",
    "trip": "trip",
    "tickets": "ticket",
}
# Old apps without models: only migration rows, if any
LEGACY_APP_LABELS = tuple(LEGACY_MODELS) + ("accounts", "default", "healthcheck")


class Command(BaseCommand):
    help = "Moves an existing database from the old apps/* layout to the single `app` application."

    def add_arguments(self, parser):
        parser.add_argument("--database", default=DEFAULT_DB_ALIAS)

    def handle(self, *args, database, **options):
        connection = connections[database]
        tables = set(connection.introspection.table_names())
        if MigrationRecorder.Migration._meta.db_table not in tables:
            return

        recorder = MigrationRecorder(connection)
        legacy_rows = recorder.migration_qs.filter(app__in=LEGACY_APP_LABELS)
        if not legacy_rows.exists():
            return

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        app_migrations = sorted(name for label, name in loader.disk_migrations if label == APP_LABEL)
        if not app_migrations:
            raise CommandError(ErrorMessages.LEGACY_MIGRATIONS_MISSING)

        missing = sorted(
            model._meta.db_table
            for model in apps.get_app_config(APP_LABEL).get_models()
            if model._meta.db_table not in tables
        )
        if missing:
            raise CommandError(f"Legacy tables not found, nothing was changed: {', '.join(missing)}")

        with transaction.atomic(using=database):
            content_types = ContentType.objects.db_manager(database)
            for old_label, model in LEGACY_MODELS.items():
                legacy = content_types.filter(app_label=old_label, model=model).first()
                if legacy is None:
                    continue
                # A `migrate` run before this command may have created an
                # empty app.<model> type (and its permissions): it gives way.
                content_types.filter(app_label=APP_LABEL, model=model).exclude(pk=legacy.pk).delete()
                legacy.app_label = APP_LABEL
                legacy.save(update_fields=["app_label"])

            applied = {name for label, name in recorder.applied_migrations() if label == APP_LABEL}
            for name in app_migrations:
                if name not in applied:
                    recorder.record_applied(APP_LABEL, name)
            legacy_rows.delete()

        ContentType.objects.clear_cache()
        self.stdout.write(self.style.SUCCESS(f"Adopted the legacy schema into `{APP_LABEL}`: {', '.join(app_migrations)}"))

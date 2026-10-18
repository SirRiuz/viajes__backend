from unittest import mock

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError, call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase

LOADER = "app.management.commands.adopt_legacy_schema.MigrationLoader"


class AdoptLegacySchemaTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        # --no-migrations skips django_migrations. Created before the test
        # transaction opens: SQLite can't change its schema inside one.
        MigrationRecorder(connection).ensure_schema()
        super().setUpClass()

    def setUp(self):
        self.recorder = MigrationRecorder(connection)
        self.recorder.migration_qs.all().delete()

    def with_disk_migrations(self, *names):
        loader = mock.patch(LOADER)
        self.addCleanup(loader.stop)
        loader.start().return_value.disk_migrations = {("app", n): None for n in names}

    def legacy_database(self):
        """What the old apps/* layout left: its migration rows and content types."""
        for label in ("users", "driver", "route", "vessel", "trip", "tickets", "honeypot"):
            self.recorder.record_applied(label, "0001_initial")
        self.recorder.record_applied("admin", "0001_initial")
        legacy = ContentType.objects.create(app_label="driver", model="driver")
        Permission.objects.create(content_type=legacy, codename="legacy_driver_perm", name="legacy")
        return legacy

    def test_fresh_database_is_left_alone(self):
        self.with_disk_migrations("0001_initial")
        call_command("adopt_legacy_schema")
        self.assertFalse(self.recorder.migration_qs.exists())

    def test_legacy_database_is_adopted_once(self):
        self.with_disk_migrations("0001_initial")
        legacy = self.legacy_database()

        call_command("adopt_legacy_schema")

        applied = set(self.recorder.applied_migrations())
        self.assertIn(("app", "0001_initial"), applied)
        self.assertIn(("honeypot", "0001_initial"), applied)
        self.assertIn(("admin", "0001_initial"), applied)
        self.assertFalse({label for label, _ in applied} & {"users", "driver", "route", "vessel", "trip", "tickets"})
        # The old content type (and so its permissions) now belongs to `app`
        legacy.refresh_from_db()
        self.assertEqual((legacy.app_label, legacy.model), ("app", "driver"))
        self.assertEqual(ContentType.objects.filter(model="driver").count(), 1)
        self.assertTrue(Permission.objects.filter(content_type=legacy, codename="legacy_driver_perm").exists())

        call_command("adopt_legacy_schema")  # second run: nothing to do
        self.assertEqual(self.recorder.migration_qs.filter(app="app").count(), 1)

    def test_refuses_without_generated_migrations(self):
        self.with_disk_migrations()
        self.legacy_database()
        with self.assertRaisesMessage(CommandError, "make migrations"):
            call_command("adopt_legacy_schema")
        self.assertTrue(self.recorder.migration_qs.filter(app="driver").exists())

    def test_database_without_migration_table(self):
        with mock.patch.object(connection.introspection, "table_names", return_value=[]):
            call_command("adopt_legacy_schema")

    def test_refuses_when_legacy_tables_are_missing(self):
        self.with_disk_migrations("0001_initial")
        self.legacy_database()
        tables = [t for t in connection.introspection.table_names() if t != "driver_driver"]
        with mock.patch.object(connection.introspection, "table_names", return_value=tables):
            with self.assertRaisesMessage(CommandError, "driver_driver"):
                call_command("adopt_legacy_schema")
        self.assertFalse(self.recorder.migration_qs.filter(app="app").exists())

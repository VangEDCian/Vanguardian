from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.identity.models import IdentityPermission, Role, RolePermission


class PermissionCatalogSyncCommandTests(TestCase):
    permission_code = "SUBJECT.PERIOD_OVERRIDE"
    permission_label = "Override subject treatment period transition"

    def test_sync_creates_permission_catalog_without_role_grants(self):
        Role.objects.create(
            study_id=1,
            code="DATA_MANAGER",
            name="Data Manager",
        )
        output = StringIO()

        call_command("sync_permission_catalog", stdout=output)

        permission = IdentityPermission.objects.get(
            app_label="edc",
            codename=self.permission_code,
        )
        self.assertEqual(permission.name, self.permission_label)
        self.assertFalse(RolePermission.objects.exists())
        self.assertIn("Permission catalog sync complete:", output.getvalue())

    def test_sync_updates_label_and_is_idempotent(self):
        permission = IdentityPermission.objects.create(
            app_label="edc",
            codename=self.permission_code,
            name="Old label",
        )

        call_command("sync_permission_catalog")
        call_command("sync_permission_catalog")

        permission.refresh_from_db()
        self.assertEqual(permission.name, self.permission_label)
        self.assertEqual(
            IdentityPermission.objects.filter(
                app_label="edc",
                codename=self.permission_code,
            ).count(),
            1,
        )

    def test_dry_run_reports_changes_without_writing(self):
        output = StringIO()

        call_command(
            "sync_permission_catalog",
            "--dry-run",
            stdout=output,
        )

        self.assertFalse(
            IdentityPermission.objects.filter(
                app_label="edc",
                codename=self.permission_code,
            ).exists()
        )
        self.assertIn(
            "Permission catalog dry run complete:",
            output.getvalue(),
        )

from io import BytesIO

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook

from apps.identity.application.services.role_permission_import import IdentityRolePermissionImportService
from apps.identity.models import Role


class IdentityRolePermissionImportServiceTests(TestCase):
    def _build_workbook_upload(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(
            [
                "role_name",
                "group_name",
                "Accss Level From DMP",
                "permission",
            ]
        )
        worksheet.append(
            [
                "Data Coordinator",
                "Data Coordinator",
                "Lock/Freeze; Compare",
                "dashboard.test_import_permission",
            ]
        )
        worksheet.append(
            [
                "Data Coordinator",
                "Missing Group",
                "Lock/Freeze; Compare",
                "dashboard.test_import_permission",
            ]
        )
        worksheet.append(
            [
                "Data Coordinator",
                "Data Coordinator",
                "Lock/Freeze; Compare",
                "dashboard.missing_permission",
            ]
        )

        buffer = BytesIO()
        workbook.save(buffer)
        return SimpleUploadedFile(
            "role_group_permission_proposal.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_import_creates_study_role_and_skips_missing_group_or_permission(self):
        content_type = ContentType.objects.create(app_label="dashboard", model="test_import")
        permission = Permission.objects.create(
            content_type=content_type,
            codename="test_import_permission",
            name="Can test import permission",
        )
        group = Group.objects.get(name="Data Coordinator")

        result = IdentityRolePermissionImportService().import_workbook(
            study_id=3,
            import_file=self._build_workbook_upload(),
        )

        self.assertEqual(result["total_rows"], 3)
        self.assertEqual(result["imported_rows"], 1)
        self.assertEqual(result["skipped_rows"], 2)
        self.assertEqual(result["created_roles"], 1)
        self.assertEqual(result["role_group_links"], 1)
        self.assertEqual(result["group_permission_links"], 1)
        self.assertEqual(result["role_permission_links"], 1)
        self.assertIn("Row 3: group 'Missing Group' does not exist.", result["issues"])
        self.assertIn("Row 4: permission 'dashboard.missing_permission' does not exist.", result["issues"])

        role = Role.objects.get(study_id=3, name="Data Coordinator")
        self.assertEqual(role.description, "Lock/Freeze; Compare")
        self.assertEqual(list(role.groups.values_list("pk", flat=True)), [group.pk])
        self.assertEqual(list(role.permissions.values_list("pk", flat=True)), [permission.pk])
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
        self.assertFalse(Role.objects.filter(study_id=4, name="Data Coordinator").exists())

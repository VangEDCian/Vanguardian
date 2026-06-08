from io import BytesIO

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook

from apps.identity.application.services.role_permission_import import IdentityRolePermissionImportService
from apps.identity.models import Role, RoleScopeLevel


class IdentityRolePermissionImportServiceTests(TestCase):
    def _build_workbook_upload(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(
            [
                "role_name",
                "group_name",
                "scope_level",
                "description",
                "permission",
            ]
        )
        worksheet.append(
            [
                "Site Coordinator",
                "Site Coordinator",
                "STUDY_SITE",
                "Input/edit/data; Query response",
                "dashboard.test_import_permission",
            ]
        )
        worksheet.append(
            [
                "Site Coordinator",
                "Missing Group",
                "STUDY_SITE",
                "Input/edit/data; Query response",
                "dashboard.test_import_permission",
            ]
        )
        worksheet.append(
            [
                "Site Coordinator",
                "Site Coordinator",
                "STUDY_SITE",
                "Input/edit/data; Query response",
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
        group = Group.objects.get(name="Site Coordinator")

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

        role = Role.objects.get(study_id=3, name="Site Coordinator")
        self.assertEqual(role.description, "Input/edit/data; Query response")
        self.assertEqual(role.scope_level, RoleScopeLevel.STUDY_SITE)
        self.assertEqual(list(role.groups.values_list("pk", flat=True)), [group.pk])
        self.assertEqual(list(role.permissions.values_list("pk", flat=True)), [permission.pk])
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
        self.assertFalse(Role.objects.filter(study_id=4, name="Site Coordinator").exists())

    def test_import_skips_invalid_scope_level(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["role_name", "group_name", "scope_level", "description", "permission"])
        worksheet.append(["Study Reviewer", "Site Coordinator", "SITE", "Review source", "dashboard.test_import_permission"])
        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile(
            "role_group_permission_proposal.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        result = IdentityRolePermissionImportService().import_workbook(
            study_id=3,
            import_file=upload,
        )

        self.assertEqual(result["imported_rows"], 0)
        self.assertEqual(result["skipped_rows"], 1)
        self.assertIn("Row 2: invalid scope_level 'SITE'.", result["issues"])

    def test_import_updates_existing_role_scope_level(self):
        content_type = ContentType.objects.create(app_label="dashboard", model="test_import_scope")
        Permission.objects.create(
            content_type=content_type,
            codename="test_import_permission",
            name="Can test import permission",
        )
        Role.objects.create(
            study_id=3,
            name="Study Reviewer",
            code="STUDY_REVIEWER",
            scope_level=RoleScopeLevel.STUDY_SITE,
        )
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["role_name", "group_name", "scope_level", "description", "permission"])
        worksheet.append(
            [
                "Study Reviewer",
                "Site Coordinator",
                "STUDY",
                "Study-level reviewer",
                "dashboard.test_import_permission",
            ]
        )
        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile(
            "role_group_permission_proposal.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        result = IdentityRolePermissionImportService().import_workbook(
            study_id=3,
            import_file=upload,
        )

        role = Role.objects.get(study_id=3, name="Study Reviewer")
        self.assertEqual(result["updated_roles"], 1)
        self.assertEqual(role.scope_level, RoleScopeLevel.STUDY)
        self.assertEqual(role.description, "Study-level reviewer")

    def test_import_rejects_csv_upload(self):
        upload = SimpleUploadedFile(
            "role_group_permission_proposal.csv",
            b"role_name,group_name,description,permission\n",
            content_type="text/csv",
        )

        with self.assertRaisesMessage(ValueError, "Only .xlsx and .xlsm files are supported."):
            IdentityRolePermissionImportService().import_workbook(
                study_id=3,
                import_file=upload,
            )

    def test_create_role_links_existing_groups_and_permissions(self):
        content_type = ContentType.objects.create(app_label="study", model="test_role_create")
        permission = Permission.objects.create(
            content_type=content_type,
            codename="create_role_permission",
            name="Can create role permission",
        )
        group = Group.objects.create(name="Role Creators")

        result = IdentityRolePermissionImportService().create_role(
            study_id=5,
            name="Study Reviewer",
            code="STUDY_REVIEWER",
            description="Review source data",
            scope_level=RoleScopeLevel.STUDY,
            group_ids=(group.pk,),
            permission_ids=(permission.pk,),
        )

        role = Role.objects.get(study_id=5, name="Study Reviewer")
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["permission_count"], 1)
        self.assertEqual(role.code, "STUDY_REVIEWER")
        self.assertEqual(role.scope_level, RoleScopeLevel.STUDY)
        self.assertEqual(list(role.groups.values_list("pk", flat=True)), [group.pk])
        self.assertEqual(list(role.permissions.values_list("pk", flat=True)), [permission.pk])

    def test_create_role_rejects_duplicate_study_role_name(self):
        Role.objects.create(
            study_id=5,
            name="Study Reviewer",
            code="STUDY_REVIEWER",
            scope_level=RoleScopeLevel.STUDY,
        )

        with self.assertRaises(ValueError):
            IdentityRolePermissionImportService().create_role(
                study_id=5,
                name="Study Reviewer",
            )

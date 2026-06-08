from pathlib import Path

from django.template import Context, Template
from django.test import SimpleTestCase


class StudyManageRolesTemplateTests(SimpleTestCase):
    def test_study_tabs_include_manage_roles_link(self):
        rendered = Template('{% include "study/components/_study_detail_tabs.html" with study_active_tab="manage_roles" %}').render(Context({"detail_study": {"id": 1}}))

        self.assertIn('href="/studies/1/roles"', rendered)
        self.assertIn("Manage Roles", rendered)
        self.assertIn("is-active", rendered)

    def test_manage_roles_template_has_import_footer(self):
        template_path = Path(__file__).resolve().parents[2] / "src/templates/study/study_manage_roles.html"
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn('data-modal-open="modal-import-role-permission"', template_source)
        self.assertIn("Import Role Permission", template_source)
        self.assertIn("_role_permission_import_modal.html", template_source)

    def test_role_permission_import_modal_has_template_download_and_actions(self):
        template_path = Path(__file__).resolve().parents[2] / "src/templates/study/components/_role_permission_import_modal.html"
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn('id="modal-import-role-permission"', template_source)
        self.assertIn('enctype="multipart/form-data"', template_source)
        self.assertIn('name="import_file"', template_source)
        self.assertIn('accept=".xlsx,.xlsm"', template_source)
        self.assertIn("role_permissions_import_template.xlsx", template_source)
        self.assertIn("scope_level", template_source)
        self.assertIn("Download Template", template_source)
        self.assertIn("Import File", template_source)
        self.assertIn("Cancel", template_source)

    def test_manage_roles_template_has_create_new_role_link(self):
        template_path = Path(__file__).resolve().parents[2] / "src/templates/study/study_manage_roles.html"
        template_source = template_path.read_text(encoding="utf-8")
        urls_path = Path(__file__).resolve().parents[2] / "src/apps/study/presentation/web/urls.py"
        urls_source = urls_path.read_text(encoding="utf-8")

        self.assertIn("role_create_url", template_source)
        self.assertIn("Create New Role", template_source)
        self.assertIn('path("studies/<int:study_id>/roles/create"', urls_source)

    def test_role_create_template_has_create_role_form(self):
        template_path = Path(__file__).resolve().parents[2] / "src/templates/study/study_role_create.html"
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn("Create Roles", template_source)
        self.assertIn("role_create_group_options", template_source)
        self.assertIn("role_create_permission_options", template_source)
        self.assertIn("role_manage_url", template_source)

    def test_role_create_template_field_order_matches_manage_roles_flow(self):
        template_path = Path(__file__).resolve().parents[2] / "src/templates/study/study_role_create.html"
        template_source = template_path.read_text(encoding="utf-8")

        ordered_labels = (
            "Role Code",
            "Role Name",
            "Scope",
            "Description",
            "Groups",
            "Permissions",
        )
        positions = [template_source.index(label) for label in ordered_labels]

        self.assertEqual(positions, sorted(positions))

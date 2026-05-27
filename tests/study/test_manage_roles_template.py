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

        self.assertIn('enctype="multipart/form-data"', template_source)
        self.assertIn('name="import_file"', template_source)
        self.assertIn("Import Role Permission", template_source)

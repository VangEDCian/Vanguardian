from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.utils.datastructures import MultiValueDict

from apps.study.application import CrfTemplateImportFormatError, ImportStudyCrfTemplateFieldsTemplateResult
from apps.study.application.commands.import_crf_template_fields_template import CrfTemplateFieldImportIssue
from apps.study.presentation.web.forms import (
    CrfSectionLayoutConfigImportTemplateForm,
    CrfTemplateFieldsImportTemplateForm,
    CrfValidationRuleImportTemplateForm,
)
from apps.study.presentation.web.views.crf_templates import StudyCrfTemplateFieldImportTemplateView


class CrfTemplateFieldsImportTemplateFormTests(SimpleTestCase):
    def test_import_file_accepts_multiple_workbooks(self):
        files = MultiValueDict(
            {
                "import_file": [
                    SimpleUploadedFile("crf_template_fields_import_visit1.xlsx", b"file-1"),
                    SimpleUploadedFile("crf_template_fields_import_visit2.xls", b"file-2"),
                ]
            }
        )

        form = CrfTemplateFieldsImportTemplateForm(data={}, files=files)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.fields["import_file"].widget.allow_multiple_selected)
        self.assertIn("multiple", str(form["import_file"]))
        self.assertEqual(
            [uploaded_file.name for uploaded_file in form.cleaned_data["import_file"]],
            [
                "crf_template_fields_import_visit1.xlsx",
                "crf_template_fields_import_visit2.xls",
            ],
        )

    def test_import_file_rejects_invalid_extension_in_multiple_selection(self):
        files = MultiValueDict(
            {
                "import_file": [
                    SimpleUploadedFile("crf_template_fields_import_visit1.xlsx", b"file-1"),
                    SimpleUploadedFile("not-a-workbook.txt", b"file-2"),
                ]
            }
        )

        form = CrfTemplateFieldsImportTemplateForm(data={}, files=files)

        self.assertFalse(form.is_valid())
        self.assertIn("import_file", form.errors)


class CrfSectionLayoutConfigImportTemplateFormTests(SimpleTestCase):
    def test_import_file_accepts_workbook(self):
        files = {"import_file": SimpleUploadedFile("section_layout_configs.xlsx", b"file")}

        form = CrfSectionLayoutConfigImportTemplateForm(data={}, files=files)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["import_file"].name, "section_layout_configs.xlsx")
        self.assertIn("id_section_layout_config_import_file", str(form["import_file"]))

    def test_import_file_rejects_invalid_extension(self):
        files = {"import_file": SimpleUploadedFile("section_layout_configs.csv", b"file")}

        form = CrfSectionLayoutConfigImportTemplateForm(data={}, files=files)

        self.assertFalse(form.is_valid())
        self.assertIn("import_file", form.errors)


class CrfValidationRuleImportTemplateFormTests(SimpleTestCase):
    def test_import_file_accepts_workbook(self):
        files = {"import_file": SimpleUploadedFile("validation_rules.xlsx", b"file")}

        form = CrfValidationRuleImportTemplateForm(data={}, files=files)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["import_file"].name, "validation_rules.xlsx")
        self.assertIn("id_validation_rule_import_file", str(form["import_file"]))

    def test_import_file_rejects_invalid_extension(self):
        files = {"import_file": SimpleUploadedFile("validation_rules.csv", b"file")}

        form = CrfValidationRuleImportTemplateForm(data={}, files=files)

        self.assertFalse(form.is_valid())
        self.assertIn("import_file", form.errors)


class StudyCrfTemplateFieldImportTemplateViewTests(SimpleTestCase):
    def test_import_field_template_files_aggregates_each_workbook_result(self):
        class FakeImportService:
            def execute(self, command):
                if command.file_name == "visit1.xlsx":
                    return ImportStudyCrfTemplateFieldsTemplateResult(
                        total_rows=2,
                        created_count=1,
                        updated_count=1,
                        skipped_count=0,
                    )
                return ImportStudyCrfTemplateFieldsTemplateResult(
                    total_rows=1,
                    created_count=0,
                    updated_count=0,
                    skipped_count=1,
                    issues=(
                        CrfTemplateFieldImportIssue(
                            sheet_name="Template Fields",
                            row_number=3,
                            identifier="AE.AETERM",
                            reason="Field Name is required.",
                        ),
                    ),
                )

        view = StudyCrfTemplateFieldImportTemplateView()
        view._study = SimpleNamespace(pk=17)
        view.get_import_crf_template_fields_template_service = FakeImportService

        result = view._import_field_template_files(
            uploaded_files=[
                SimpleUploadedFile("visit1.xlsx", b"file-1"),
                SimpleUploadedFile("visit2.xlsx", b"file-2"),
            ],
            actor_user_id=9,
        )

        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.issues[0].sheet_name, "visit2.xlsx / Template Fields")

    def test_import_field_template_files_continues_after_file_level_error(self):
        class FakeImportService:
            def execute(self, command):
                if command.file_name == "invalid.xlsx":
                    raise CrfTemplateImportFormatError("Required worksheet: Template Fields.")
                return ImportStudyCrfTemplateFieldsTemplateResult(
                    total_rows=1,
                    created_count=1,
                    updated_count=0,
                    skipped_count=0,
                )

        view = StudyCrfTemplateFieldImportTemplateView()
        view._study = SimpleNamespace(pk=17)
        view.get_import_crf_template_fields_template_service = FakeImportService

        result = view._import_field_template_files(
            uploaded_files=[
                SimpleUploadedFile("invalid.xlsx", b"not-workbook"),
                SimpleUploadedFile("visit1.xlsx", b"file-1"),
            ],
            actor_user_id=9,
        )

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.issues[0].identifier, "invalid.xlsx")

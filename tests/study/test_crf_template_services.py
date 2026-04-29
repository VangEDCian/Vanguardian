from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.study.application.services import (
    ImportStudyCrfTemplatesTemplateService,
    StudyCrfTemplateDirectoryQueryService,
)


def _make_crf_template(*, pk, code, name, version, is_active=True, updated_at=None):
    return SimpleNamespace(
        pk=pk,
        code=code,
        version=version,
        is_active=is_active,
        updated_at=updated_at,
        safe_translation_getter=lambda field_name, default="", any_language=False: name if field_name == "name" else default,
    )


class StudyCrfTemplateDirectoryQueryServiceTests(SimpleTestCase):
    def test_filters_using_translated_name(self):
        adapter = SimpleNamespace(
            list_study_templates_for_listing=lambda study_id: [
                _make_crf_template(pk=2, code="LAB", name="Laboratory", version="v2"),
                _make_crf_template(pk=1, code="AE", name="Adverse Event", version="v1"),
            ]
        )

        result = StudyCrfTemplateDirectoryQueryService(
            crf_context_adapter=adapter,
        ).list_crf_templates(
            study_id=3,
            search_query="adverse",
            sort_query="name",
        )

        self.assertEqual(result["crf_templates_total"], 1)
        self.assertEqual(
            result["crf_templates"][0].safe_translation_getter("name", default="", any_language=True),
            "Adverse Event",
        )


class ImportStudyCrfTemplatesTemplateServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ImportStudyCrfTemplatesTemplateService()

    def test_static_template_contains_required_sheet_and_headers(self):
        workbook = load_workbook(
            Path(__file__).resolve().parents[2] / "src/staticfiles/study/templates/crf_templates_import_template.xlsx",
            read_only=True,
        )

        self.assertEqual(workbook.sheetnames, ["Form Templates", "Section Templates"])
        self.assertEqual(
            list(next(workbook["Form Templates"].iter_rows(values_only=True))),
            list(self.service.expected_columns["Form Templates"]),
        )

    @patch.object(
        ImportStudyCrfTemplatesTemplateService,
        "_load_rows_from_workbook",
        return_value={
            "Form Templates": [
                (2, {"code": "AE", "vi_name": "Bien co bat loi", "en_name": "Adverse Event", "version": "v1"})
            ],
            "Section Templates": [],
        },
    )
    def test_execute_imports_crf_sheet(self, mock_load_rows):
        call_order = []

        def import_form_template_row(**kwargs):
            call_order.append(("crf", kwargs["row_number"]))
            return "created", 101, "AE"

        self.service._import_form_template_row = import_form_template_row

        result = self.service.execute(
            command=SimpleNamespace(
                actor_user_id=7,
                selected_study_id=3,
                study_id=3,
                file_name="crf_templates_import_template.xlsx",
                file_content=b"xlsx",
            )
        )

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 0)
        self.assertEqual(call_order, [("crf", 2)])

    def test_import_crf_template_row_calls_context_adapter(self):
        mock_adapter = MagicMock()
        mock_adapter.upsert_crf_template.return_value = "updated"
        mock_adapter.resolve_unique_template_by_code_version.return_value = SimpleNamespace(pk=17, code="AE")

        service = ImportStudyCrfTemplatesTemplateService(
            crf_context_adapter=mock_adapter,
        )

        outcome = service._import_form_template_row(
            selected_study_id=7,
            study_id=7,
            row_data={
                "code": "AE",
                "vi_name": "Bien co bat loi",
                "en_name": "Adverse Event",
                "version": "v1.0",
            },
            row_number=2,
            actor_user_id=11,
        )

        self.assertEqual(outcome, ("updated", 17, "AE"))
        mock_adapter.upsert_crf_template.assert_called_once()

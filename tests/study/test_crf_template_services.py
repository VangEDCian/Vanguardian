from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.study.application.commands.import_crf_templates_template import (
    ImportStudyCrfTemplatesTemplateService,
)
from apps.study.application.queries.study_crf_template_directory import (
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
    @patch("apps.study.application.queries.study_crf_template_directory.CrfTemplate")
    def test_filters_and_sorts_using_translated_name(self, mock_crf_template):
        mock_crf_template.objects.filter.return_value.prefetch_related.return_value = [
            _make_crf_template(pk=2, code="LAB", name="Laboratory", version="v2"),
            _make_crf_template(pk=1, code="AE", name="Adverse Event", version="v1"),
        ]

        result = StudyCrfTemplateDirectoryQueryService().list_crf_templates(
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

    def test_static_template_contains_required_sheets_and_headers(self):
        workbook = load_workbook(
            Path(__file__).resolve().parents[2] / "src/staticfiles/study/templates/crf_templates_import_template.xlsx",
            read_only=True,
        )

        self.assertEqual(workbook.sheetnames, ["CRF Templates", "Page Templates"])
        self.assertEqual(
            list(next(workbook["CRF Templates"].iter_rows(values_only=True))),
            list(self.service.expected_columns["CRF Templates"]),
        )
        self.assertEqual(
            list(next(workbook["Page Templates"].iter_rows(values_only=True))),
            list(self.service.expected_columns["Page Templates"]),
        )

    @patch("apps.study.application.commands.import_crf_templates_template.transaction.atomic")
    @patch.object(
        ImportStudyCrfTemplatesTemplateService,
        "_load_rows_from_workbook",
        return_value={
            "CRF Templates": [(2, {"code": "AE", "vi_name": "Bien co bat loi", "en_name": "Adverse Event", "version": "v1"})],
            "Page Templates": [(2, {"crf_code": "AE", "code": "AE01", "vi_name": "Tong quan", "en_name": "Overview", "order": "1"})],
        },
    )
    def test_execute_imports_crf_sheet_before_page_sheet(
        self,
        mock_load_rows,
        mock_atomic,
    ):
        mock_atomic.return_value = nullcontext()
        call_order = []

        def import_crf_template_row(**kwargs):
            call_order.append(("crf", kwargs["row_number"]))
            return "created"

        def import_page_template_row(**kwargs):
            call_order.append(("page", kwargs["row_number"]))
            return "updated"

        self.service._import_crf_template_row = import_crf_template_row
        self.service._import_page_template_row = import_page_template_row

        result = self.service.execute(
            command=SimpleNamespace(
                actor_user_id=7,
                study_id=3,
                file_name="crf_templates_import_template.xlsx",
                file_content=b"xlsx",
            )
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(call_order, [("crf", 2), ("page", 2)])

    @patch("apps.study.application.commands.import_crf_templates_template.transaction.atomic")
    @patch("apps.study.application.commands.import_crf_templates_template.CrfTemplate")
    def test_import_crf_template_row_persists_vi_and_en_translations(self, mock_crf_template_cls, mock_atomic):
        mock_atomic.return_value = nullcontext()
        existing_template = MagicMock()
        mock_crf_template_cls.objects.filter.return_value.first.return_value = existing_template

        outcome = self.service._import_crf_template_row(
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

        self.assertEqual(outcome, "updated")
        self.assertEqual(existing_template.set_current_language.call_args_list[0].args[:1], ("vi",))
        self.assertEqual(existing_template.set_current_language.call_args_list[1].args[:1], ("en",))
        self.assertEqual(existing_template.name, "Adverse Event")
        existing_template.save.assert_called_once_with()

    @patch("apps.study.application.commands.import_crf_templates_template.transaction.atomic")
    @patch("apps.study.application.commands.import_crf_templates_template.CrfPageTemplate")
    @patch("apps.study.application.commands.import_crf_templates_template.CrfTemplate")
    def test_import_page_template_row_persists_vi_and_en_titles(
        self,
        mock_crf_template_cls,
        mock_page_template_cls,
        mock_atomic,
    ):
        mock_atomic.return_value = nullcontext()
        crf_template = MagicMock()
        page_template = MagicMock()
        mock_crf_template_cls.objects.filter.return_value.order_by.return_value.first.return_value = crf_template
        mock_crf_template_cls.objects.filter.return_value.exclude.return_value.exists.return_value = False
        mock_page_template_cls.objects.filter.return_value.first.return_value = page_template

        outcome = self.service._import_page_template_row(
            study_id=7,
            row_data={
                "crf_code": "AE",
                "code": "AE01",
                "vi_name": "Tong quan",
                "en_name": "Overview",
                "order": "2",
            },
            row_number=3,
            actor_user_id=11,
        )

        self.assertEqual(outcome, "updated")
        self.assertEqual(page_template.set_current_language.call_args_list[0].args[:1], ("vi",))
        self.assertEqual(page_template.set_current_language.call_args_list[1].args[:1], ("en",))
        self.assertEqual(page_template.title, "Overview")
        page_template.save.assert_called_once_with()

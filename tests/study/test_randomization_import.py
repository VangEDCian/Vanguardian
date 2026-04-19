from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.study.application.commands.import_randomization import (
    PreviewRandomizationImportCommand,
    PreviewStudyRandomizationArmsImportService,
)
from apps.study.application.use_cases.randomization_import_preview import (
    RandomizationArmImportPreviewUseCase,
    RandomizationSchemeImportPreviewUseCase,
)


class RandomizationSchemeImportPreviewUseCaseTests(SimpleTestCase):
    def setUp(self):
        self.use_case = RandomizationSchemeImportPreviewUseCase()

    def test_static_template_headers_match_expected_columns(self):
        workbook = load_workbook(
            Path(__file__).resolve().parents[2] / "src/staticfiles/study/templates/randomization_scheme_template.xlsx",
            read_only=True,
        )
        worksheet = workbook.worksheets[0]
        headers = list(next(worksheet.iter_rows(values_only=True)))

        self.assertEqual(
            [str(header).strip() for header in headers],
            [column.label.strip() for column in self.use_case.columns],
        )

    def test_execute_parses_csv_and_converts_integer_and_boolean_columns(self):
        csv_content = "\n".join(
            [
                "Code,Name,Type,Target Randomized Total,Is Open Label,Requires Screening Pass,Eligibility Rule Code",
                "SCH-001,Main Scheme,block,100,Yes,No,ELIG-01",
            ]
        ).encode("utf-8")

        result = self.use_case.execute(
            file_name="randomization_scheme.csv",
            file_content=csv_content,
        )

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.issues, ())
        self.assertEqual(result.preview_rows[0].values[3], 100)
        self.assertTrue(result.preview_rows[0].values[4])
        self.assertFalse(result.preview_rows[0].values[5])
        self.assertEqual(result.parsed_rows[0].values["target_randomized_total"], 100)

    def test_execute_reports_duplicate_scheme_codes(self):
        csv_content = "\n".join(
            [
                "Code,Name,Type,Target Randomized Total,Is Open Label,Requires Screening Pass,Eligibility Rule Code",
                "SCH-001,Main Scheme,block,100,Yes,No,ELIG-01",
                "SCH-001,Backup Scheme,block,120,No,Yes,ELIG-02",
            ]
        ).encode("utf-8")

        result = self.use_case.execute(
            file_name="randomization_scheme.csv",
            file_content=csv_content,
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].row_number, 3)
        self.assertEqual(result.issues[0].column_label, "Code")


class RandomizationArmImportPreviewTests(SimpleTestCase):
    def test_static_template_headers_match_expected_columns(self):
        workbook = load_workbook(
            Path(__file__).resolve().parents[2] / "src/staticfiles/study/templates/randomization_arms_template.xlsx",
            read_only=True,
        )
        worksheet = workbook.worksheets[0]
        headers = list(next(worksheet.iter_rows(values_only=True)))

        self.assertEqual(
            [str(header).strip() for header in headers],
            [column.label.strip() for column in RandomizationArmImportPreviewUseCase.columns],
        )

    @patch("apps.study.application.commands.import_randomization.PreviewStudyRandomizationArmsImportService.randomization_scheme_model")
    def test_preview_service_adds_issue_for_unknown_scheme_code(self, mock_scheme_model):
        mock_values_list = MagicMock(return_value=["SCH-EXISTING"])
        mock_scheme_model.objects.filter.return_value.values_list = mock_values_list

        preview_service = PreviewStudyRandomizationArmsImportService()
        command = PreviewRandomizationImportCommand(
            actor_user_id=9,
            study_id=3,
            file_name="randomization_arms.csv",
            file_content="\n".join(
                [
                    "Scheme Code,Code,Name,Target Count,Display Order",
                    "SCH-MISSING,ARM-A,Active Comparator,50,1",
                ]
            ).encode("utf-8"),
        )

        result = preview_service.execute(command)

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].column_label, "Scheme Code")
        self.assertIn("SCH-MISSING", result.issues[0].reason)




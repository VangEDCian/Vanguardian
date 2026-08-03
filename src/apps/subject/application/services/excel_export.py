from dataclasses import dataclass
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from apps.subject.infrastructure.repositories.subject_excel_export import (
    DjangoSubjectExcelExportRepository,
)

EXCEL_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
MAX_EXCEL_COLUMNS = 16_384


class SubjectExcelExportSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class SubjectExcelExportResult:
    content: bytes
    filename: str
    subject_count: int
    field_count: int


class _StudyExportCatalogAdapter:
    @staticmethod
    def list_groups(*, study_id: int) -> list[dict]:
        from apps.study.public import list_subject_export_field_groups

        return list_subject_export_field_groups(study_id=study_id)


class _DataCaptureExportAdapter:
    @staticmethod
    def read_values(**kwargs) -> dict:
        from apps.datacapture.public import read_subject_export_values

        return read_subject_export_values(**kwargs)


class SubjectExcelExportService:
    repository_class = DjangoSubjectExcelExportRepository
    field_catalog_adapter_class = _StudyExportCatalogAdapter
    data_capture_adapter_class = _DataCaptureExportAdapter

    def __init__(
        self,
        repository=None,
        field_catalog_adapter=None,
        data_capture_adapter=None,
    ):
        self.repository = repository or self.repository_class()
        self.field_catalog_adapter = (
            field_catalog_adapter or self.field_catalog_adapter_class()
        )
        self.data_capture_adapter = (
            data_capture_adapter or self.data_capture_adapter_class()
        )

    def export(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
        selected_field_tokens: tuple[str, ...],
    ) -> SubjectExcelExportResult:
        selected_fields = self._resolve_selected_fields(
            study_id=study_id,
            selected_field_tokens=selected_field_tokens,
        )
        subject_rows = self.repository.list_scoped_subject_rows(
            study_id=study_id,
            site_id=site_id,
            subject_ids=subject_ids,
        )
        if not subject_rows:
            raise SubjectExcelExportSelectionError(
                "No selected subjects are available in the current study site."
            )

        scoped_subject_ids = tuple(int(row["id"]) for row in subject_rows)
        values_by_subject_id = self.data_capture_adapter.read_values(
            study_id=study_id,
            site_id=site_id,
            subject_ids=scoped_subject_ids,
            field_specs=selected_fields,
        )
        workbook_content = self._build_workbook(
            subject_rows=subject_rows,
            selected_fields=selected_fields,
            values_by_subject_id=values_by_subject_id,
        )
        timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        return SubjectExcelExportResult(
            content=workbook_content,
            filename=f"subjects-{study_id}-{timestamp}.xlsx",
            subject_count=len(subject_rows),
            field_count=len(selected_fields),
        )

    def _resolve_selected_fields(
        self,
        *,
        study_id: int,
        selected_field_tokens: tuple[str, ...],
    ) -> tuple[dict, ...]:
        normalized_tokens = tuple(
            dict.fromkeys(
                str(token).strip()
                for token in selected_field_tokens
                if str(token).strip()
            )
        )
        if not normalized_tokens:
            raise SubjectExcelExportSelectionError(
                "Select at least one field to export."
            )

        groups = self.field_catalog_adapter.list_groups(study_id=study_id)
        catalog_fields = tuple(
            field
            for group in groups
            for form in group["forms"]
            for field in form["fields"]
        )
        fields_by_token = {field["token"]: field for field in catalog_fields}
        unknown_tokens = [
            token for token in normalized_tokens if token not in fields_by_token
        ]
        if unknown_tokens:
            raise SubjectExcelExportSelectionError(
                "One or more selected export fields are invalid."
            )
        selected_token_set = set(normalized_tokens)
        selected_fields = tuple(
            field
            for field in catalog_fields
            if field["token"] in selected_token_set
        )
        if len(selected_fields) + 3 > MAX_EXCEL_COLUMNS:
            raise SubjectExcelExportSelectionError(
                "Too many fields were selected for one Excel worksheet."
            )
        return selected_fields

    @classmethod
    def _build_workbook(
        cls,
        *,
        subject_rows: tuple[dict, ...],
        selected_fields: tuple[dict, ...],
        values_by_subject_id: dict[int, dict],
    ) -> bytes:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Subjects"
        headers = [
            "subject_id",
            "subject_code",
            "screening_code",
            *(field["header"] for field in selected_fields),
        ]
        worksheet.append(headers)
        cls._style_header(worksheet)

        for subject in subject_rows:
            subject_id = int(subject["id"])
            subject_values = values_by_subject_id.get(subject_id, {})
            row_values = [
                subject_id,
                subject.get("subject_code") or "",
                subject.get("screening_code") or "",
                *(
                    subject_values.get(field["token"], "")
                    for field in selected_fields
                ),
            ]
            worksheet.append(row_values)
            cls._force_formula_like_strings_to_text(
                worksheet,
                row_index=worksheet.max_row,
                values=row_values,
            )

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        cls._set_column_widths(worksheet, headers)
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    @staticmethod
    def _style_header(worksheet):
        fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
        for cell in worksheet[1]:
            cell.font = Font(bold=True, color="17324D")
            cell.fill = fill
            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

    @staticmethod
    def _force_formula_like_strings_to_text(worksheet, *, row_index, values):
        for column_index, value in enumerate(values, start=1):
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                worksheet.cell(
                    row=row_index,
                    column=column_index,
                ).data_type = "s"

    @staticmethod
    def _set_column_widths(worksheet, headers):
        for column_index, header in enumerate(headers, start=1):
            worksheet.column_dimensions[
                worksheet.cell(row=1, column=column_index).column_letter
            ].width = min(max(len(str(header)) + 2, 14), 60)


__all__ = [
    "EXCEL_CONTENT_TYPE",
    "SubjectExcelExportResult",
    "SubjectExcelExportSelectionError",
    "SubjectExcelExportService",
]

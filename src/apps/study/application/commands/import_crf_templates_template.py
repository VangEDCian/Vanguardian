from dataclasses import dataclass
from io import BytesIO

from django.utils import timezone

from apps.crf.public import CrfContextAdapter


@dataclass(frozen=True)
class ImportStudyCrfTemplatesTemplateCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class CrfTemplateImportIssue:
    sheet_name: str
    row_number: int
    identifier: str
    reason: str


@dataclass(frozen=True)
class ImportStudyCrfTemplatesTemplateResult:
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    issues: tuple[CrfTemplateImportIssue, ...] = ()
    warnings: tuple[str, ...] = ()


class CrfTemplateImportTemplateError(Exception):
    """Base error raised for CRF template import failures."""


class CrfTemplateImportDependencyError(CrfTemplateImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class CrfTemplateImportFormatError(CrfTemplateImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""


class ImportStudyCrfTemplatesTemplateService:
    crf_context_adapter_class = CrfContextAdapter
    crf_templates_sheet_name = "CRF Templates"
    expected_columns = {
        crf_templates_sheet_name: (
            "Code",
            "Vi Name",
            "En Name",
            "Version",
        ),
    }
    expected_header_map = {
        crf_templates_sheet_name: {
            "code": "code",
            "vi name": "vi_name",
            "en name": "en_name",
            "version": "version",
        },
    }

    def __init__(self, crf_context_adapter=None):
        self.crf_context_adapter = crf_context_adapter or self.crf_context_adapter_class()

    def execute(self, command: ImportStudyCrfTemplatesTemplateCommand) -> ImportStudyCrfTemplatesTemplateResult:
        workbook_rows_by_sheet = self._load_rows_from_workbook(
            file_name=command.file_name,
            file_content=command.file_content,
        )

        created_count = 0
        updated_count = 0
        issues = []

        for row_number, row_data in workbook_rows_by_sheet[self.crf_templates_sheet_name]:
            identifier = self._build_crf_template_identifier(row_data)
            try:
                import_outcome = self._import_crf_template_row(
                    study_id=command.study_id,
                    row_data=row_data,
                    row_number=row_number,
                    actor_user_id=command.actor_user_id,
                )
            except CrfTemplateImportFormatError as exc:
                issues.append(
                    CrfTemplateImportIssue(
                        sheet_name=self.crf_templates_sheet_name,
                        row_number=row_number,
                        identifier=identifier,
                        reason=str(exc),
                    )
                )
                continue

            if import_outcome == "created":
                created_count += 1
            else:
                updated_count += 1

        total_rows = len(workbook_rows_by_sheet[self.crf_templates_sheet_name])
        return ImportStudyCrfTemplatesTemplateResult(
            total_rows=total_rows,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=len(issues),
            issues=tuple(issues),
            warnings=(),
        )

    def _import_crf_template_row(self, *, study_id, row_data, row_number, actor_user_id):
        code = self._require_text(
            row_data.get("code"),
            field_label="Code",
            max_length=64,
        )
        vi_name = self._require_text(
            row_data.get("vi_name"),
            field_label="Vi Name",
            max_length=255,
        )
        en_name = self._require_text(
            row_data.get("en_name"),
            field_label="En Name",
            max_length=255,
        )
        version = self._require_text(
            row_data.get("version"),
            field_label="Version",
            max_length=32,
        )

        return self.crf_context_adapter.upsert_crf_template(
            study_id=study_id,
            code=code,
            version=version,
            vi_name=vi_name,
            en_name=en_name,
            actor_user_id=actor_user_id,
            now=self._now(),
        )

    def _load_rows_from_workbook(self, *, file_name, file_content):
        file_name_lower = (file_name or "").strip().lower()
        if file_name_lower.endswith(".xlsx"):
            return self._load_xlsx_rows(file_content)
        if file_name_lower.endswith(".xls"):
            return self._load_xls_rows(file_content)
        raise CrfTemplateImportFormatError("Only .xlsx and .xls files are supported.")

    def _load_xlsx_rows(self, file_content):
        try:
            from openpyxl import load_workbook
        except ModuleNotFoundError as exc:
            raise CrfTemplateImportDependencyError(
                "Excel import support for .xlsx is not installed. Install openpyxl first."
            ) from exc

        workbook = load_workbook(filename=BytesIO(file_content), data_only=True, read_only=True)
        rows_by_sheet = {}
        for sheet_name in self.expected_columns:
            if sheet_name not in workbook.sheetnames:
                raise CrfTemplateImportFormatError(f"Missing required worksheet: {sheet_name}")
            rows_by_sheet[sheet_name] = self._map_rows(
                rows=list(workbook[sheet_name].iter_rows(values_only=True)),
                sheet_name=sheet_name,
            )
        return rows_by_sheet

    def _load_xls_rows(self, file_content):
        try:
            import xlrd
        except ModuleNotFoundError as exc:
            raise CrfTemplateImportDependencyError(
                "Excel import support for .xls is not installed. Install xlrd first."
            ) from exc

        workbook = xlrd.open_workbook(file_contents=file_content)
        rows_by_sheet = {}
        for sheet_name in self.expected_columns:
            try:
                worksheet = workbook.sheet_by_name(sheet_name)
            except xlrd.biffh.XLRDError as exc:
                raise CrfTemplateImportFormatError(
                    f"Missing required worksheet: {sheet_name}"
                ) from exc
            rows_by_sheet[sheet_name] = self._map_rows(
                rows=[worksheet.row_values(index) for index in range(worksheet.nrows)],
                sheet_name=sheet_name,
            )
        return rows_by_sheet

    def _map_rows(self, *, rows, sheet_name):
        if sheet_name not in self.expected_columns:
            raise CrfTemplateImportFormatError(f"Unexpected worksheet: {sheet_name}")
        if not rows:
            return []

        headers = [self._normalize_header(value) for value in rows[0]]
        missing_headers = [
            header
            for header in self.expected_columns[sheet_name]
            if self._normalize_header(header) not in headers
        ]
        if missing_headers:
            raise CrfTemplateImportFormatError(
                f"Worksheet '{sheet_name}' is missing required columns: " + ", ".join(missing_headers)
            )

        header_keys = [self.expected_header_map[sheet_name].get(header) for header in headers]
        mapped_rows = []
        for row_index, row_values in enumerate(rows[1:], start=2):
            if self._is_blank_row(row_values):
                continue

            row_data = {}
            for column_index, header_key in enumerate(header_keys):
                if not header_key:
                    continue
                row_data[header_key] = row_values[column_index] if column_index < len(row_values) else None

            mapped_rows.append((row_index, row_data))

        return mapped_rows

    @staticmethod
    def _normalize_header(value):
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def _is_blank_row(row_values):
        return all(str(value or "").strip() == "" for value in row_values)

    @staticmethod
    def _as_text(value):
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    def _require_text(self, value, *, field_label, max_length):
        normalized_value = self._as_text(value)
        if not normalized_value:
            raise CrfTemplateImportFormatError(f"{field_label} is required.")
        if len(normalized_value) > max_length:
            raise CrfTemplateImportFormatError(
                f"{field_label} must be {max_length} characters or fewer."
            )
        return normalized_value

    def _build_crf_template_identifier(self, row_data):
        return " / ".join(
            part for part in (
                self._as_text(row_data.get("code")),
                self._as_text(row_data.get("version")),
            ) if part
        )

    @staticmethod
    def _now():
        return timezone.now()

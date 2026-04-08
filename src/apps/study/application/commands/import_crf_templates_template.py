from dataclasses import dataclass
from io import BytesIO

from django.db import transaction
from django.utils import timezone

from apps.crf.models import CrfTemplate


@dataclass(frozen=True)
class ImportStudyCrfTemplatesTemplateCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class CrfTemplateImportIssue:
    row_number: int
    code: str
    version: str
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
    expected_columns = (
        "Code",
        "Name",
        "Version",
    )
    expected_header_map = {
        "code": "code",
        "name": "name",
        "version": "version",
    }

    def execute(self, command: ImportStudyCrfTemplatesTemplateCommand) -> ImportStudyCrfTemplatesTemplateResult:
        workbook_rows = self._load_rows_from_workbook(
            file_name=command.file_name,
            file_content=command.file_content,
        )

        created_count = 0
        updated_count = 0
        issues = []

        for row_number, row_data in workbook_rows:
            try:
                import_outcome = self._import_row(
                    study_id=command.study_id,
                    row_data=row_data,
                    row_number=row_number,
                    actor_user_id=command.actor_user_id,
                )
            except CrfTemplateImportFormatError as exc:
                issues.append(
                    CrfTemplateImportIssue(
                        row_number=row_number,
                        code=str(row_data.get("code", "") or ""),
                        version=str(row_data.get("version", "") or ""),
                        reason=str(exc),
                    )
                )
                continue

            if import_outcome == "created":
                created_count += 1
            else:
                updated_count += 1

        return ImportStudyCrfTemplatesTemplateResult(
            total_rows=len(workbook_rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=len(issues),
            issues=tuple(issues),
            warnings=(),
        )

    def _import_row(self, *, study_id, row_data, row_number, actor_user_id):
        code = self._as_text(row_data.get("code"))
        if not code:
            raise CrfTemplateImportFormatError("Code is required.")
        if len(code) > 64:
            raise CrfTemplateImportFormatError("Code must be 64 characters or fewer.")

        name = self._as_text(row_data.get("name"))
        if not name:
            raise CrfTemplateImportFormatError("Name is required.")
        if len(name) > 255:
            raise CrfTemplateImportFormatError("Name must be 255 characters or fewer.")

        version = self._as_text(row_data.get("version"))
        if not version:
            raise CrfTemplateImportFormatError("Version is required.")
        if len(version) > 32:
            raise CrfTemplateImportFormatError("Version must be 32 characters or fewer.")

        now = self._now()
        defaults = {
            "name": name,
            "deleted": False,
            "is_active": True,
            "updated_at": now,
            "updated_by_id": actor_user_id,
        }

        with transaction.atomic():
            crf_template = CrfTemplate.objects.filter(
                study_id=study_id,
                code=code,
                version=version,
            ).first()

            if crf_template is None:
                CrfTemplate.objects.create(
                    study_id=study_id,
                    code=code,
                    version=version,
                    created_at=now,
                    created_by_id=actor_user_id,
                    **defaults,
                )
                return "created"

            for field_name, value in defaults.items():
                setattr(crf_template, field_name, value)
            crf_template.save(update_fields=list(defaults.keys()))
            return "updated"

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
        worksheet = workbook.worksheets[0]
        rows = list(worksheet.iter_rows(values_only=True))
        return self._map_rows(rows)

    def _load_xls_rows(self, file_content):
        try:
            import xlrd
        except ModuleNotFoundError as exc:
            raise CrfTemplateImportDependencyError(
                "Excel import support for .xls is not installed. Install xlrd first."
            ) from exc

        workbook = xlrd.open_workbook(file_contents=file_content)
        worksheet = workbook.sheet_by_index(0)
        rows = [worksheet.row_values(index) for index in range(worksheet.nrows)]
        return self._map_rows(rows)

    def _map_rows(self, rows):
        if not rows:
            raise CrfTemplateImportFormatError("The workbook is empty.")

        headers = [self._normalize_header(value) for value in rows[0]]
        missing_headers = [
            header
            for header in self.expected_columns
            if self._normalize_header(header) not in headers
        ]
        if missing_headers:
            raise CrfTemplateImportFormatError(
                "Missing required columns: " + ", ".join(missing_headers)
            )

        header_keys = [self.expected_header_map.get(header) for header in headers]
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

    @staticmethod
    def _now():
        return timezone.now()

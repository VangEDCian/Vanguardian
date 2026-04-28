from dataclasses import dataclass


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

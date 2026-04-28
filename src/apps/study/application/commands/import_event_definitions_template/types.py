from dataclasses import dataclass


@dataclass(frozen=True)
class ImportStudyEventDefinitionsTemplateCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class EventDefinitionImportIssue:
    row_number: int
    study_code: str
    code: str
    reason: str


@dataclass(frozen=True)
class ImportStudyEventDefinitionsTemplateResult:
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    issues: tuple[EventDefinitionImportIssue, ...] = ()
    warnings: tuple[str, ...] = ()


class EventDefinitionImportTemplateError(Exception):
    """Base error raised for event definition template import failures."""


class EventDefinitionImportDependencyError(EventDefinitionImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class EventDefinitionImportFormatError(EventDefinitionImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""

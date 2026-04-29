from dataclasses import dataclass


@dataclass(frozen=True)
class ImportStudyEventFormBindingsTemplateCommand:
    actor_user_id: int
    selected_study_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class EventFormBindingImportIssue:
    row_number: int
    event_code: str
    form_code: str
    reason: str


@dataclass(frozen=True)
class ImportStudyEventFormBindingsTemplateResult:
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    issues: tuple[EventFormBindingImportIssue, ...] = ()
    warnings: tuple[str, ...] = ()


class EventFormBindingImportTemplateError(Exception):
    """Base error raised for event form binding template import failures."""


class EventFormBindingImportDependencyError(EventFormBindingImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class EventFormBindingImportFormatError(EventFormBindingImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""

__all__ = [
    "EventFormBindingImportDependencyError",
    "EventFormBindingImportFormatError",
    "EventFormBindingImportIssue",
    "EventFormBindingImportTemplateError",
    "ImportStudyEventFormBindingsTemplateCommand",
    "ImportStudyEventFormBindingsTemplateResult",
]

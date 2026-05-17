from dataclasses import dataclass

from apps.study.application.exceptions import (
    EventFormBindingImportDependencyError as EventFormBindingImportDependencyError,
)
from apps.study.application.exceptions import (
    EventFormBindingImportFormatError as EventFormBindingImportFormatError,
)
from apps.study.application.exceptions import (
    EventFormBindingImportTemplateError as EventFormBindingImportTemplateError,
)


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


__all__ = [
    "EventFormBindingImportDependencyError",
    "EventFormBindingImportFormatError",
    "EventFormBindingImportIssue",
    "EventFormBindingImportTemplateError",
    "ImportStudyEventFormBindingsTemplateCommand",
    "ImportStudyEventFormBindingsTemplateResult",
]

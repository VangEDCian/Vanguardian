from dataclasses import dataclass

from apps.study.application.exceptions import (
    EventDefinitionImportDependencyError as EventDefinitionImportDependencyError,
)
from apps.study.application.exceptions import (
    EventDefinitionImportFormatError as EventDefinitionImportFormatError,
)
from apps.study.application.exceptions import (
    EventDefinitionImportTemplateError as EventDefinitionImportTemplateError,
)


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

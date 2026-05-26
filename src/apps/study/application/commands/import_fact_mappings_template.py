from dataclasses import dataclass

from apps.study.application.exceptions import (
    FactMappingImportDependencyError as FactMappingImportDependencyError,
)
from apps.study.application.exceptions import (
    FactMappingImportFormatError as FactMappingImportFormatError,
)
from apps.study.application.exceptions import (
    FactMappingImportTemplateError as FactMappingImportTemplateError,
)


@dataclass(frozen=True)
class ImportStudyFactMappingsTemplateCommand:
    actor_user_id: int
    selected_study_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class FactMappingImportIssue:
    row_number: int
    event_code: str
    form_code: str
    fact_key: str
    reason: str


@dataclass(frozen=True)
class ImportStudyFactMappingsTemplateResult:
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    issues: tuple[FactMappingImportIssue, ...] = ()
    warnings: tuple[str, ...] = ()


__all__ = [
    "FactMappingImportDependencyError",
    "FactMappingImportFormatError",
    "FactMappingImportIssue",
    "FactMappingImportTemplateError",
    "ImportStudyFactMappingsTemplateCommand",
    "ImportStudyFactMappingsTemplateResult",
]

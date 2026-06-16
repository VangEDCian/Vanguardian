from dataclasses import dataclass

from apps.study.application.exceptions import (
    CrfTemplateImportDependencyError as CrfTemplateImportDependencyError,
)
from apps.study.application.exceptions import (
    CrfTemplateImportFormatError as CrfTemplateImportFormatError,
)
from apps.study.application.exceptions import (
    CrfTemplateImportTemplateError as CrfTemplateImportTemplateError,
)


@dataclass(frozen=True)
class ImportStudyCrfTemplatesTemplateCommand:
    actor_user_id: int
    selected_study_id: int
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

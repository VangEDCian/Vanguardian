from dataclasses import dataclass

from apps.study.application.exceptions import (
    CrfTemplateImportDependencyError as CrfTemplateImportDependencyError,
)
from apps.study.application.exceptions import (
    CrfTemplateImportFormatError as CrfTemplateImportFormatError,
)


@dataclass(frozen=True)
class ImportStudyCrfSectionLayoutConfigsTemplateCommand:
    actor_user_id: int
    selected_study_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class CrfSectionLayoutConfigImportIssue:
    sheet_name: str
    row_number: int
    identifier: str
    reason: str


@dataclass(frozen=True)
class ImportStudyCrfSectionLayoutConfigsTemplateResult:
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    issues: tuple[CrfSectionLayoutConfigImportIssue, ...] = ()
    warnings: tuple[str, ...] = ()


__all__ = [
    "CrfSectionLayoutConfigImportIssue",
    "CrfTemplateImportDependencyError",
    "CrfTemplateImportFormatError",
    "ImportStudyCrfSectionLayoutConfigsTemplateCommand",
    "ImportStudyCrfSectionLayoutConfigsTemplateResult",
]

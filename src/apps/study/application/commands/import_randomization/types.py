from dataclasses import dataclass

from apps.study.application.exceptions import (
    RandomizationImportValidationError as RandomizationImportValidationError,
)


@dataclass(frozen=True)
class PreviewRandomizationImportCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class CommitRandomizationImportCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class CommitRandomizationImportResult:
    total_rows: int
    created_count: int
    updated_count: int

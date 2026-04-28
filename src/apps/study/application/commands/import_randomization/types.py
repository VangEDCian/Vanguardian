from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from apps.study.application.use_cases.randomization_import_preview import RandomizationImportIssue


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


class RandomizationImportValidationError(Exception):
    """Raised when the uploaded file contains row-level validation issues."""

    def __init__(self, issues: tuple[RandomizationImportIssue, ...]):
        super().__init__(str(_("The uploaded file contains validation issues.")))
        self.issues = issues

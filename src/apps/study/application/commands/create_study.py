from dataclasses import dataclass
from datetime import date

from apps.study.domain import (
    DEFAULT_SCREENING_CODE_PATTERN,
    DEFAULT_SUBJECT_CODE_PATTERN,
    ScreeningIdentifierMode,
    SubjectCodeUniquenessScope,
    SubjectIdentifierMode,
)


@dataclass(frozen=True)
class CreateStudyCommand:
    code: str
    name: str
    sponsor: str
    description: str
    is_active: bool
    actor_user_id: int
    start_date: date | None = None
    end_date: date | None = None
    subject_identifier_mode: str = SubjectIdentifierMode.GENERATED_AT_ENROLLMENT
    screening_identifier_mode: str = ScreeningIdentifierMode.GENERATED
    subject_code_pattern: str = DEFAULT_SUBJECT_CODE_PATTERN
    screening_code_pattern: str = DEFAULT_SCREENING_CODE_PATTERN
    subject_code_uniqueness_scope: str = SubjectCodeUniquenessScope.STUDY_SITE
    lock_subject_code_after_assignment: bool = True

__all__ = ["CreateStudyCommand"]

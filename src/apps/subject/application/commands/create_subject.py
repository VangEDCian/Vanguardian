from dataclasses import dataclass

from apps.subject.application.exceptions import StudyNotFoundError


@dataclass(frozen=True)
class CreateSubjectCommand:
    study_id: int
    site_id: int
    actor_user_id: int

__all__ = [
    "CreateSubjectCommand",
    "StudyNotFoundError",
]

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteStudyCommand:
    study_id: int
    actor_user_id: int

__all__ = ["DeleteStudyCommand"]

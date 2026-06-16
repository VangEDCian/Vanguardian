from dataclasses import dataclass


@dataclass(frozen=True)
class ToggleStudyStatusCommand:
    study_id: int
    actor_user_id: int

__all__ = ["ToggleStudyStatusCommand"]

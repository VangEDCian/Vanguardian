from dataclasses import dataclass
from datetime import date


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

__all__ = ["CreateStudyCommand"]

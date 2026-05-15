from dataclasses import dataclass, field
from typing import Any

from apps.subject.application.exceptions import SubjectEventInstanceNotFoundError


@dataclass(frozen=True)
class TriggerSubjectEventTransitionCommand:
    source_event_instance_id: int
    facts: dict[str, Any] = field(default_factory=dict)
    actor_user_id: int | None = None
    trigger_source: str = "system"


__all__ = [
    "SubjectEventInstanceNotFoundError",
    "TriggerSubjectEventTransitionCommand",
]

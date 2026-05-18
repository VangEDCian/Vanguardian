from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SubjectEventInstanceSnapshot:
    id: int
    study_id: int
    subject_id: int
    event_definition_id: int
    study_version: str
    repeat_index: int
    status: str
    event_code: str | None = None
    event_name: str | None = None
    event_type: str | None = None


@dataclass(frozen=True)
class StudyEventDefinitionSnapshot:
    id: int
    study_id: int
    study_version: str
    code: str
    name: str
    event_type: str


@dataclass(frozen=True)
class StudyEventTransitionRuleSnapshot:
    id: int
    from_event_definition_id: int
    to_event_definition_id: int
    transition_type: str
    condition_scope: str
    condition_code: str | None
    condition_expression: str | None
    auto_open: bool
    auto_create: bool
    requires_previous_completion: bool
    allow_skip: bool
    display_order: int
    offset_days: int | None = None


@dataclass(frozen=True)
class SubjectEventTransitionDecision:
    rule_id: int
    target_event_definition_id: int
    should_open: bool
    should_create: bool = False
    reason: str = ""


@dataclass(frozen=True)
class SubjectEventTransitionApplied:
    subject_id: int
    source_event_instance_id: int
    target_event_instance_id: int
    rule_id: int
    from_status: str
    to_status: str
    event_name: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubjectEventTransitionResult:
    source_event_instance_id: int
    applied_events: tuple[SubjectEventTransitionApplied, ...] = ()
    skipped_decisions: tuple[SubjectEventTransitionDecision, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.applied_events)


__all__ = [
    "StudyEventDefinitionSnapshot",
    "StudyEventTransitionRuleSnapshot",
    "SubjectEventInstanceSnapshot",
    "SubjectEventTransitionApplied",
    "SubjectEventTransitionDecision",
    "SubjectEventTransitionResult",
]

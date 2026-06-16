from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RecordEventGateEvaluationCommand:
    study_id: int
    subject_id: int
    event_definition_id: int
    event_instance_id: int | None
    gate_code: str
    gate_type: str
    target_action: str
    result: str
    transition_rule_id: int | None = None
    evaluated_by_id: int | None = None
    rule_code: str | None = None
    rule_version: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)
    failed_conditions: list[dict[str, Any]] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    source_context: str = "subject_event_transition"
    source_object_id: int | None = None
    condition_results: list[dict[str, Any]] = field(default_factory=list)


__all__ = ["RecordEventGateEvaluationCommand"]

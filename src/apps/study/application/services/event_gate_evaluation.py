import json
from dataclasses import dataclass
from datetime import datetime

from apps.study.application.commands import RecordEventGateEvaluationCommand
from apps.study.infrastructure.repositories import DjangoEventGateEvaluationRepository


class EventGateEvaluationRecorder:
    repository_class = DjangoEventGateEvaluationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def record(self, command: RecordEventGateEvaluationCommand):
        now = self.repository.now()
        gate_evaluation = self.repository.create_gate_evaluation(
            created_at=now,
            study_id=command.study_id,
            subject_id=command.subject_id,
            event_definition_id=command.event_definition_id,
            event_instance_id=command.event_instance_id,
            transition_rule_id=command.transition_rule_id,
            gate_code=command.gate_code,
            gate_type=command.gate_type,
            target_action=command.target_action,
            result=command.result,
            evaluated_at=now,
            evaluated_by_id=command.evaluated_by_id,
            rule_code=command.rule_code,
            rule_version=command.rule_version,
            facts_json=self._to_json(command.facts),
            failed_conditions_json=self._to_json(command.failed_conditions),
            blocking_reasons_json=self._to_json(command.blocking_reasons),
            source_context=command.source_context,
            source_object_id=command.source_object_id,
        )
        self.repository.bulk_create_gate_condition_results(
            gate_evaluation=gate_evaluation,
            conditions=command.condition_results,
        )
        return gate_evaluation

    @staticmethod
    def _to_json(value) -> str:
        return json.dumps(value or ([] if isinstance(value, list) else {}), ensure_ascii=True, sort_keys=True, default=str)


@dataclass(frozen=True)
class EventGateEvaluationHistoryRecord:
    occurred_at: datetime | None
    category: str
    source: str
    field_name: str
    field_description: str
    value: str
    user_display: str
    scope: str
    action: str
    from_value: str
    to_value: str
    actor: str
    reason: str
    details: tuple[dict[str, str], ...]


class EventGateEvaluationHistoryReader:
    repository_class = DjangoEventGateEvaluationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def list_for_subject(
        self,
        *,
        study_id: int,
        subject_id: int,
        limit: int = 200,
        search: str = "",
        field_name: str = "",
    ) -> list[dict]:
        rows = self.repository.list_gate_evaluation_history_for_subject(
            study_id=study_id,
            subject_id=subject_id,
            limit=limit,
            search=search,
            field_name=field_name,
        )
        return [self._to_public_dict(self._build_record(row)) for row in rows]

    @classmethod
    def _build_record(cls, row) -> EventGateEvaluationHistoryRecord:
        return EventGateEvaluationHistoryRecord(
            occurred_at=row.evaluated_at,
            category="event_gate",
            source="Event Gate",
            field_name=getattr(row, "audit_field_name", "") or row.gate_code or "event_gate",
            field_description=getattr(row, "audit_field_description", "") or cls._build_scope(row),
            value=getattr(row, "audit_value", "") or cls._build_value(row),
            user_display=getattr(row, "audit_user_display", "") or cls._format_actor(row.evaluated_by_id),
            scope=cls._build_scope(row),
            action=cls._humanize_value(row.target_action) or "Gate evaluation",
            from_value=cls._humanize_value(row.gate_type),
            to_value=cls._humanize_value(row.result),
            actor=cls._format_actor(row.evaluated_by_id),
            reason=cls._build_reason(row),
            details=tuple(cls._build_details(row)),
        )

    @classmethod
    def _build_scope(cls, row) -> str:
        event_definition = getattr(row, "event_definition", None)
        event_label = getattr(event_definition, "name", "") or getattr(event_definition, "code", "")
        return str(event_label or row.gate_code or "Event Gate").strip()

    @classmethod
    def _build_value(cls, row) -> str:
        return " ".join(
            part
            for part in (
                cls._humanize_value(row.result),
                cls._build_reason(row),
                str(row.facts_json or "").strip(),
                str(row.failed_conditions_json or "").strip(),
                str(row.blocking_reasons_json or "").strip(),
            )
            if part
        )

    @classmethod
    def _build_reason(cls, row) -> str:
        blocking_reasons = cls._load_json_list(row.blocking_reasons_json)
        if blocking_reasons:
            return ", ".join(cls._humanize_value(reason) for reason in blocking_reasons if reason)
        failed_conditions = cls._load_json_list(row.failed_conditions_json)
        if failed_conditions:
            return f"{len(failed_conditions)} failed condition(s)"
        condition_results = getattr(row, "audit_condition_results", ()) or ()
        failed_count = sum(1 for condition in condition_results if condition.result in {"fail", "error"})
        if failed_count:
            return f"{failed_count} failed condition(s)"
        return ""

    @classmethod
    def _build_details(cls, row) -> list[dict[str, str]]:
        condition_results = getattr(row, "audit_condition_results", ()) or ()
        details = [
            ("Gate Code", row.gate_code),
            ("Rule", row.rule_code),
            ("Rule Version", row.rule_version),
            ("Source", row.source_context),
            ("Condition Results", len(condition_results)),
        ]
        return [
            {"label": label, "value": str(value)}
            for label, value in details
            if cls._has_value(value)
        ]

    @staticmethod
    def _format_actor(actor_id) -> str:
        if actor_id is None:
            return "System"
        return f"User #{actor_id}"

    @staticmethod
    def _load_json_list(value: str | None) -> list:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if isinstance(parsed, list):
            return parsed
        return []

    @staticmethod
    def _humanize_value(value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return text.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _has_value(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    @staticmethod
    def _to_public_dict(record: EventGateEvaluationHistoryRecord) -> dict:
        return {
            "occurred_at": record.occurred_at,
            "category": record.category,
            "source": record.source,
            "field_name": record.field_name,
            "field_description": record.field_description,
            "value": record.value,
            "user_display": record.user_display,
            "scope": record.scope,
            "action": record.action,
            "from_value": record.from_value,
            "to_value": record.to_value,
            "actor": record.actor,
            "reason": record.reason,
            "details": list(record.details),
        }


__all__ = [
    "EventGateEvaluationHistoryReader",
    "EventGateEvaluationHistoryRecord",
    "EventGateEvaluationRecorder",
]

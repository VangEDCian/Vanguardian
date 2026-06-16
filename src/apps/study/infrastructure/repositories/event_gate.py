from django.utils import timezone

from apps.study.models import EventGateConditionResult, EventGateEvaluation


class DjangoEventGateEvaluationRepository:
    def now(self):
        return timezone.now()

    def create_gate_evaluation(self, **values):
        return EventGateEvaluation.objects.create(**values)

    def bulk_create_gate_condition_results(self, *, gate_evaluation, conditions: list[dict]):
        rows = [
            EventGateConditionResult(
                gate_evaluation=gate_evaluation,
                condition_order=condition.get("condition_order") or index,
                fact_key=condition.get("fact_key") or "",
                source_context=condition.get("source_context") or "subject_event_transition",
                source_object_type=condition.get("source_object_type") or "transition_rule",
                source_object_id=condition.get("source_object_id"),
                operator=condition.get("operator") or "eq",
                expected_value=condition.get("expected_value"),
                actual_value=condition.get("actual_value"),
                value_type=condition.get("value_type") or "json",
                result=condition.get("result") or "fail",
                reason_code=condition.get("reason_code"),
                reason_message=condition.get("reason_message"),
            )
            for index, condition in enumerate(conditions, start=1)
        ]
        if rows:
            EventGateConditionResult.objects.bulk_create(rows)
        return rows


__all__ = ["DjangoEventGateEvaluationRepository"]

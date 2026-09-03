from django.db.models import CharField, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Cast, Coalesce, Concat
from django.utils import timezone

from apps.identity.models import User
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

    def list_gate_evaluation_history_for_subject(
        self,
        *,
        study_id: int,
        subject_id: int,
        limit: int = 200,
        search: str = "",
        field_name: str = "",
    ) -> list:
        condition_results = EventGateConditionResult.objects.order_by("condition_order", "id")
        queryset = (
            EventGateEvaluation.objects.filter(
                study_id=study_id,
                subject_id=subject_id,
            )
            .select_related(
                "event_definition",
                "transition_rule",
                "transition_rule__from_event_definition",
                "transition_rule__to_event_definition",
            )
            .prefetch_related(
                Prefetch(
                    "condition_results",
                    queryset=condition_results,
                    to_attr="audit_condition_results",
                )
            )
            .annotate(
                audit_field_name=Coalesce("gate_code", Value("event_gate"), output_field=CharField()),
                audit_field_description=Concat(
                    Coalesce("event_definition__name", "event_definition__code", Value("")),
                    Value(" / "),
                    Coalesce("target_action", Value("")),
                    Value(" / "),
                    Coalesce("rule_code", Value("")),
                    output_field=CharField(),
                ),
                audit_value=Concat(
                    Coalesce("result", Value("")),
                    Value(" "),
                    Coalesce("facts_json", Value("")),
                    Value(" "),
                    Coalesce("failed_conditions_json", Value("")),
                    Value(" "),
                    Coalesce("blocking_reasons_json", Value("")),
                    output_field=CharField(),
                ),
                audit_user_display=self._audit_user_display_expression("evaluated_by_id"),
            )
        )
        queryset = self._apply_audit_history_filters(
            queryset,
            search=search,
            field_name=field_name,
        )
        queryset = queryset.order_by("-evaluated_at", "-id")
        if limit:
            queryset = queryset[:limit]
        return list(queryset)

    @classmethod
    def _apply_audit_history_filters(cls, queryset, *, search: str = "", field_name: str = ""):
        normalized_field_name = str(field_name or "").strip()
        if normalized_field_name:
            queryset = queryset.filter(audit_field_name__icontains=normalized_field_name)

        for term in cls._audit_history_search_terms(search):
            queryset = queryset.filter(
                Q(audit_value__icontains=term)
                | Q(audit_field_description__icontains=term)
                | Q(audit_user_display__icontains=term)
            )
        return queryset

    @staticmethod
    def _audit_history_search_terms(search: str) -> tuple[str, ...]:
        normalized_search = str(search or "").strip()
        if not normalized_search:
            return ()
        return tuple(term for term in normalized_search.split() if term)

    @staticmethod
    def _audit_user_display_expression(actor_field: str):
        user_display = (
            User.objects.filter(pk=OuterRef(actor_field), deleted=False)
            .annotate(
                audit_display=Concat(
                    Coalesce("display_name", Value("")),
                    Value(" "),
                    Coalesce("first_name", Value("")),
                    Value(" "),
                    Coalesce("last_name", Value("")),
                    Value(" "),
                    Coalesce("username", Value("")),
                    output_field=CharField(),
                )
            )
            .values("audit_display")[:1]
        )
        return Coalesce(
            Cast(Subquery(user_display), output_field=CharField()),
            Value("System"),
            output_field=CharField(),
        )


__all__ = ["DjangoEventGateEvaluationRepository"]

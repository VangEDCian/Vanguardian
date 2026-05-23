from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.core.choices import EligibilityAssessmentStatusChoices
from apps.study.models import (
    ConditionDefinition,
    EventDefinition,
    EventGateConditionResult,
    EventGateEvaluation,
    SubjectEligibilityAssessment,
    SubjectEligibilityFailure,
)


class DjangoEligibilityAssessmentRepository:
    def now(self):
        return timezone.now()

    def actor_has_permission(self, *, actor_id: int | None, permission_codename: str) -> bool:
        if actor_id is None:
            return True
        user = get_user_model().objects.filter(pk=actor_id, is_active=True).first()
        if user is None:
            return False
        return user.has_perm(f"study.{permission_codename}")

    def list_active_eligibility_conditions(self, *, study_id: int, study_version: str, rule_code: str | None = None):
        queryset = ConditionDefinition.objects.filter(
            study_id=study_id,
            study_version=study_version,
            scope="eligibility",
            status="active",
            deleted=False,
        )
        if rule_code:
            queryset = queryset.filter(code=rule_code)
        return list(queryset.order_by("id"))

    def next_assessment_no(self, *, subject_id: int, assessment_type: str) -> int:
        latest = (
            SubjectEligibilityAssessment.objects.filter(
                subject_id=subject_id,
                assessment_type=assessment_type,
            )
            .order_by("-assessment_no")
            .values_list("assessment_no", flat=True)
            .first()
        )
        return (latest or 0) + 1

    def supersede_current_assessments(
        self,
        *,
        subject_id: int,
        assessment_type: str,
        actor_id: int | None,
        now,
    ):
        current_assessments = list(
            SubjectEligibilityAssessment.objects.select_for_update().filter(
                subject_id=subject_id,
                assessment_type=assessment_type,
                is_current=True,
                deleted=False,
            )
        )
        for assessment in current_assessments:
            assessment.is_current = False
            if assessment.assessment_status != EligibilityAssessmentStatusChoices.RETRACTED:
                assessment.assessment_status = EligibilityAssessmentStatusChoices.SUPERSEDED
            assessment.updated_at = now
            assessment.updated_by_id = actor_id
            assessment.save(update_fields=["is_current", "assessment_status", "updated_at", "updated_by_id"])
        return current_assessments

    def create_assessment(self, **values):
        return SubjectEligibilityAssessment.objects.create(**values)

    def bulk_create_failures(self, *, assessment, failures: list[dict], actor_id: int | None, now):
        rows = []
        for index, failure in enumerate(failures, start=1):
            rows.append(
                SubjectEligibilityFailure(
                    assessment=assessment,
                    created_at=now,
                    updated_at=now,
                    deleted=False,
                    criterion_code=failure.get("criterion_code"),
                    criterion_type=failure.get("criterion_type") or "OTHER",
                    criterion_label_snapshot=failure.get("criterion_label_snapshot"),
                    expected_value=failure.get("expected_value"),
                    actual_value=failure.get("actual_value"),
                    value_type=failure.get("value_type"),
                    source_context=failure.get("source_context"),
                    source_object_type=failure.get("source_object_type"),
                    source_object_id=failure.get("source_object_id"),
                    source_field_key=failure.get("source_field_key") or failure.get("fact_key"),
                    source_field_template_id=failure.get("source_field_template_id"),
                    reason_code=failure.get("reason_code"),
                    reason_text=failure.get("reason_text") or failure.get("reason_message"),
                    display_order=failure.get("display_order") or index,
                    created_by_id=actor_id,
                    updated_by_id=actor_id,
                )
            )
        if rows:
            SubjectEligibilityFailure.objects.bulk_create(rows)
        return rows

    def create_gate_evaluation(self, **values):
        return EventGateEvaluation.objects.create(**values)

    def bulk_create_gate_condition_results(self, *, gate_evaluation, conditions: list[dict]):
        rows = [
            EventGateConditionResult(
                gate_evaluation=gate_evaluation,
                condition_order=condition.get("condition_order") or index,
                fact_key=condition.get("fact_key") or "",
                source_context=condition.get("source_context") or "eligibility",
                source_object_type=condition.get("source_object_type") or "assessment",
                source_object_id=condition.get("source_object_id"),
                operator=condition.get("operator") or "equals",
                expected_value=condition.get("expected_value"),
                actual_value=condition.get("actual_value"),
                value_type=condition.get("value_type") or "string",
                result=condition.get("result") or "fail",
                reason_code=condition.get("reason_code"),
                reason_message=condition.get("reason_message"),
            )
            for index, condition in enumerate(conditions, start=1)
        ]
        if rows:
            EventGateConditionResult.objects.bulk_create(rows)
        return rows

    def find_gate_event_definition_id(
        self,
        *,
        study_id: int,
        study_version: str,
        preferred_codes: list[str],
    ) -> int | None:
        return (
            EventDefinition.objects.filter(
                study_id=study_id,
                study_version=study_version,
                deleted=False,
                code__in=preferred_codes,
            )
            .order_by("sequence_no", "id")
            .values_list("id", flat=True)
            .first()
        )

    def get_current_assessment(self, *, study_id: int, subject_id: int, assessment_type: str):
        return (
            SubjectEligibilityAssessment.objects.filter(
                study_id=study_id,
                subject_id=subject_id,
                assessment_type=assessment_type,
                is_current=True,
                deleted=False,
            )
            .order_by("-assessment_no", "-id")
            .first()
        )

    def get_assessment_for_update(self, *, study_id: int, subject_id: int, assessment_id: int):
        return (
            SubjectEligibilityAssessment.objects.select_for_update()
            .filter(pk=assessment_id, study_id=study_id, subject_id=subject_id, deleted=False)
            .first()
        )

    def save_assessment(self, assessment, *, update_fields):
        assessment.save(update_fields=update_fields)
        return assessment

    def list_current_final_assessments_for_source(
        self,
        *,
        source_context: str,
        source_object_type: str | None,
        source_object_id: int | None,
        source_page_state_id: int | None,
        source_page_entry_id: int | None,
        source_data_hash: str | None,
    ):
        query = Q(source_context=source_context, is_current=True, assessment_status="FINAL", deleted=False)
        source_query = Q()
        if source_object_type and source_object_id is not None:
            source_query |= Q(source_object_type=source_object_type, source_object_id=source_object_id)
        if source_page_state_id is not None:
            source_query |= Q(source_page_state_id=source_page_state_id)
        if source_page_entry_id is not None:
            source_query |= Q(source_page_entry_id=source_page_entry_id)
        if source_data_hash:
            source_query |= Q(source_data_hash=source_data_hash)
        if not source_query:
            return []
        return list(SubjectEligibilityAssessment.objects.select_for_update().filter(query & source_query))


__all__ = ["DjangoEligibilityAssessmentRepository"]

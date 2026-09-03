import json
from dataclasses import dataclass, replace
from datetime import timedelta

from django.utils import timezone

from apps.core.choices import SubjectPeriodStatusChoices
from apps.subject.models import (
    Subject,
    SubjectEventInstance,
    SubjectPeriod,
    SubjectPeriodMilestone,
    SubjectPeriodTransitionLog,
    SubjectPeriodTransitionOverride,
)


@dataclass(frozen=True)
class SubjectPeriodEventContext:
    event_instance_id: int
    subject_id: int
    status: str
    event_category: str


@dataclass(frozen=True)
class SubjectPeriodState:
    id: int
    subject_id: int
    period_no: int
    status: str
    start_event_instance_id: int | None
    end_event_instance_id: int | None
    washout_days: int | None
    transition_rule_code: str | None
    treatment_code: str = ""


@dataclass(frozen=True)
class SubjectPeriodOverrideContext:
    current_period: SubjectPeriodState
    next_period: SubjectPeriodState
    source_event_status: str | None


@dataclass(frozen=True)
class SubjectPeriodEventSnapshot:
    event_instance_id: int
    event_definition_id: int
    event_code: str
    event_status: str
    sequence_no: int


class DjangoSubjectPeriodLifecycleRepository:
    def now(self):
        return timezone.now()

    def get_event_context(self, *, event_instance_id: int) -> SubjectPeriodEventContext | None:
        event = (
            SubjectEventInstance.objects.select_related("event_definition")
            .filter(pk=event_instance_id, deleted=False)
            .only(
                "id",
                "subject_id",
                "status",
                "event_definition__event_category",
            )
            .first()
        )
        if event is None:
            return None
        return SubjectPeriodEventContext(
            event_instance_id=event.pk,
            subject_id=event.subject_id,
            status=event.status,
            event_category=event.event_definition.event_category or "",
        )

    def list_periods_for_update(self, *, subject_id: int) -> list[SubjectPeriodState]:
        return self._to_period_states(
            SubjectPeriod.objects.select_for_update()
            .select_related("sequence_period")
            .filter(subject_id=subject_id, deleted=False)
            .order_by("period_no", "id")
        )

    def get_manual_override_context(
        self,
        *,
        subject_id: int,
    ) -> SubjectPeriodOverrideContext | None:
        periods = self._to_period_states(
            SubjectPeriod.objects.select_related("sequence_period")
            .filter(subject_id=subject_id, deleted=False)
            .order_by("period_no", "id")
        )
        current_index = next(
            (
                index
                for index, period in enumerate(periods)
                if period.status
                in {
                    SubjectPeriodStatusChoices.ACTIVE,
                    SubjectPeriodStatusChoices.WASHOUT,
                }
            ),
            None,
        )
        if current_index is None or current_index + 1 >= len(periods):
            return None
        current_period = periods[current_index]
        next_period = periods[current_index + 1]
        if next_period.status != SubjectPeriodStatusChoices.PLANNED:
            return None
        return SubjectPeriodOverrideContext(
            current_period=current_period,
            next_period=next_period,
            source_event_status=self.get_event_status(
                event_instance_id=current_period.end_event_instance_id,
            ),
        )

    def get_subject_lifecycle_status_for_update(
        self,
        *,
        study_id: int,
        subject_id: int,
    ) -> str | None:
        return (
            Subject.objects.select_for_update()
            .filter(
                pk=subject_id,
                study_id=study_id,
                deleted=False,
            )
            .values_list("lifecycle_status", flat=True)
            .first()
        )

    def get_subject_lifecycle_status(self, *, subject_id: int) -> str | None:
        return (
            Subject.objects.filter(
                pk=subject_id,
                deleted=False,
            )
            .values_list("lifecycle_status", flat=True)
            .first()
        )

    def get_event_status(self, *, event_instance_id: int | None) -> str | None:
        if event_instance_id is None:
            return None
        return (
            SubjectEventInstance.objects.filter(
                pk=event_instance_id,
                deleted=False,
            )
            .values_list("status", flat=True)
            .first()
        )

    def list_period_event_snapshots(
        self,
        *,
        period: SubjectPeriodState,
    ) -> tuple[SubjectPeriodEventSnapshot, ...]:
        boundary_events = {
            event.pk: event
            for event in SubjectEventInstance.objects.select_related(
                "event_definition"
            ).filter(
                pk__in={
                    period.start_event_instance_id,
                    period.end_event_instance_id,
                },
                subject_id=period.subject_id,
                deleted=False,
            )
        }
        start_event = boundary_events.get(period.start_event_instance_id)
        end_event = boundary_events.get(period.end_event_instance_id)
        if start_event is None or end_event is None:
            return ()

        event_instances = (
            SubjectEventInstance.objects.select_related("event_definition")
            .filter(
                subject_id=period.subject_id,
                deleted=False,
                event_definition__deleted=False,
                event_definition__is_enabled=True,
                event_definition__sequence_no__gte=(
                    start_event.event_definition.sequence_no
                ),
                event_definition__sequence_no__lte=(
                    end_event.event_definition.sequence_no
                ),
            )
            .order_by("event_definition__sequence_no", "repeat_index", "id")
        )
        return tuple(
            SubjectPeriodEventSnapshot(
                event_instance_id=event.pk,
                event_definition_id=event.event_definition_id,
                event_code=event.event_definition.code,
                event_status=event.status,
                sequence_no=event.event_definition.sequence_no,
            )
            for event in event_instances
        )

    def transition_period(
        self,
        *,
        period: SubjectPeriodState,
        to_status: str,
        source_event_instance_id: int | None,
        trigger_source: str,
        reason: str,
        facts: dict,
        actor_user_id: int | None,
        now,
    ) -> SubjectPeriodState:
        from_status = self._normalize_period_status(period.status)
        to_status = self._normalize_period_status(to_status)
        if from_status == to_status:
            return period

        SubjectPeriod.objects.filter(pk=period.id).update(
            status=to_status,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        SubjectPeriodTransitionLog.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            period_id=period.id,
            subject_id=period.subject_id,
            source_event_instance_id=source_event_instance_id,
            from_status=from_status,
            to_status=to_status,
            trigger_source=trigger_source,
            reason=reason,
            facts_json=json.dumps(facts, ensure_ascii=True, sort_keys=True, default=str),
            actor_user_id=actor_user_id,
        )
        return replace(period, status=to_status)

    def record_period_end(
        self,
        *,
        period: SubjectPeriodState,
        source_event_instance_id: int | None,
        occurred_at,
        actor_user_id: int | None,
    ) -> None:
        self._upsert_actual_milestone(
            period_id=period.id,
            milestone_code="PERIOD_END_ACTUAL",
            source_event_instance_id=source_event_instance_id,
            occurred_at=occurred_at,
            actor_user_id=actor_user_id,
        )
        if not period.washout_days:
            return
        self._upsert_actual_milestone(
            period_id=period.id,
            milestone_code="WASHOUT_START_ACTUAL",
            source_event_instance_id=source_event_instance_id,
            occurred_at=occurred_at,
            actor_user_id=actor_user_id,
        )
        SubjectPeriodMilestone.objects.update_or_create(
            period_id=period.id,
            milestone_code="WASHOUT_END_PLANNED",
            defaults={
                "planned_at": occurred_at + timedelta(days=period.washout_days),
                "status": "planned",
                "source_context": "subject",
                "source_object_type": "study_eventinstance",
                "source_object_id": source_event_instance_id,
                "recorded_at": occurred_at,
                "recorded_by_id": actor_user_id,
            },
        )

    def record_washout_end(
        self,
        *,
        period: SubjectPeriodState,
        source_event_instance_id: int | None,
        occurred_at,
        actor_user_id: int | None,
    ) -> None:
        self._upsert_actual_milestone(
            period_id=period.id,
            milestone_code="WASHOUT_END_ACTUAL",
            source_event_instance_id=source_event_instance_id,
            occurred_at=occurred_at,
            actor_user_id=actor_user_id,
        )

    def record_period_start(
        self,
        *,
        period: SubjectPeriodState,
        source_event_instance_id: int | None,
        occurred_at,
        actor_user_id: int | None,
    ) -> None:
        self._upsert_actual_milestone(
            period_id=period.id,
            milestone_code="PERIOD_START_ACTUAL",
            source_event_instance_id=source_event_instance_id,
            occurred_at=occurred_at,
            actor_user_id=actor_user_id,
        )

    def correct_period_end(
        self,
        *,
        period: SubjectPeriodState,
        source_event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> None:
        SubjectPeriodMilestone.objects.filter(
            period_id=period.id,
            milestone_code__in={
                "PERIOD_END_ACTUAL",
                "WASHOUT_START_ACTUAL",
            },
        ).update(
            actual_at=None,
            status="corrected",
            correction_reason="source_event_reopened",
            source_object_id=source_event_instance_id,
            recorded_at=now,
            recorded_by_id=actor_user_id,
        )

    def list_due_washout_subject_ids(self, *, as_of, limit: int) -> list[int]:
        return list(
            SubjectPeriod.objects.filter(
                deleted=False,
                status=SubjectPeriodStatusChoices.WASHOUT,
                milestones__milestone_code="WASHOUT_END_PLANNED",
                milestones__planned_at__lte=as_of,
            )
            .order_by("milestones__planned_at", "subject_id")
            .values_list("subject_id", flat=True)
            .distinct()[:limit]
        )

    def is_washout_due(
        self,
        *,
        period: SubjectPeriodState,
        as_of,
    ) -> bool:
        if not period.washout_days:
            return True
        return SubjectPeriodMilestone.objects.filter(
            period_id=period.id,
            milestone_code="WASHOUT_END_PLANNED",
            planned_at__lte=as_of,
        ).exists()

    def create_transition_override(
        self,
        *,
        subject_id: int,
        current_period: SubjectPeriodState,
        next_period: SubjectPeriodState,
        period_end_at,
        next_period_start_at,
        reason_code: str,
        reason_text: str,
        pending_data_acknowledged: bool,
        clinical_transition_confirmed: bool,
        source_event_status: str | None,
        pending_data_snapshot: dict,
        actor_user_id: int | None,
        now,
    ) -> int:
        transition_override = SubjectPeriodTransitionOverride.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            subject_id=subject_id,
            from_period_id=current_period.id,
            to_period_id=next_period.id,
            source_event_instance_id=current_period.end_event_instance_id,
            period_end_at=period_end_at,
            next_period_start_at=next_period_start_at,
            reason_code=reason_code,
            reason_text=reason_text,
            pending_data_acknowledged=pending_data_acknowledged,
            clinical_transition_confirmed=clinical_transition_confirmed,
            source_event_status=source_event_status,
            pending_data_snapshot_json=json.dumps(
                pending_data_snapshot,
                ensure_ascii=True,
                sort_keys=True,
                default=str,
            ),
            status="applied",
            actor_user_id=actor_user_id,
        )
        return transition_override.pk

    @staticmethod
    def _upsert_actual_milestone(
        *,
        period_id: int,
        milestone_code: str,
        source_event_instance_id: int | None,
        occurred_at,
        actor_user_id: int | None,
    ) -> None:
        SubjectPeriodMilestone.objects.update_or_create(
            period_id=period_id,
            milestone_code=milestone_code,
            defaults={
                "actual_at": occurred_at,
                "status": "confirmed",
                "source_context": "subject",
                "source_object_type": "study_eventinstance",
                "source_object_id": source_event_instance_id,
                "recorded_at": occurred_at,
                "recorded_by_id": actor_user_id,
                "correction_reason": None,
            },
        )

    @staticmethod
    def _normalize_period_status(status) -> str:
        normalized = str(status or "").strip().lower()
        valid_statuses = {choice.value for choice in SubjectPeriodStatusChoices}
        return (
            normalized
            if normalized in valid_statuses
            else SubjectPeriodStatusChoices.PLANNED
        )

    @classmethod
    def _to_period_states(cls, periods) -> list[SubjectPeriodState]:
        return [
            SubjectPeriodState(
                id=period.pk,
                subject_id=period.subject_id,
                period_no=period.period_no,
                status=cls._normalize_period_status(period.status),
                start_event_instance_id=period.start_event_instance_id,
                end_event_instance_id=period.end_event_instance_id,
                washout_days=getattr(period.sequence_period, "washout_days", None),
                transition_rule_code=getattr(
                    period.sequence_period,
                    "transition_rule_code",
                    None,
                ),
                treatment_code=period.treatment_code,
            )
            for period in periods
        ]


__all__ = [
    "DjangoSubjectPeriodLifecycleRepository",
    "SubjectPeriodEventContext",
    "SubjectPeriodEventSnapshot",
    "SubjectPeriodOverrideContext",
    "SubjectPeriodState",
]

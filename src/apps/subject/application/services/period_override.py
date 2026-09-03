from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction

from apps.core.choices import SubjectLifecycleStatusChoices
from apps.subject.domain import (
    SubjectPeriodOverrideReason,
    SubjectPeriodStatus,
    SubjectPeriodTransitionPolicy,
)
from apps.subject.infrastructure.repositories.period_lifecycle import (
    DjangoSubjectPeriodLifecycleRepository,
)


def _default_pending_data_snapshot_reader(
    *,
    subject_id: int,
    event_instances: tuple[dict, ...],
) -> dict:
    from apps.datacapture.public import build_pending_period_data_snapshot
    from apps.reconcile.public import summarize_reconcile_workbench_for_page_states

    snapshot = build_pending_period_data_snapshot(
        subject_id=subject_id,
        event_instances=event_instances,
    )
    page_state_ids = tuple(
        sorted(
            {
                int(form["page_state_id"])
                for form in snapshot.get("pending_forms", ())
                if form.get("page_state_id") is not None
            }
        )
    )
    snapshot["query_summary"] = (
        summarize_reconcile_workbench_for_page_states(
            page_state_ids=page_state_ids,
        )
        if page_state_ids
        else {}
    )
    return snapshot


@dataclass(frozen=True)
class SubjectPeriodOverrideAvailability:
    available: bool
    current_period_no: int | None = None
    current_treatment_code: str = ""
    current_status: str = ""
    next_period_no: int | None = None
    next_treatment_code: str = ""
    source_event_status: str = ""


@dataclass(frozen=True)
class SubjectPeriodOverrideResult:
    applied: bool
    reason: str
    override_id: int | None = None
    current_period_no: int | None = None
    next_period_no: int | None = None


class SubjectPeriodOverrideService:
    repository_class = DjangoSubjectPeriodLifecycleRepository
    transition_policy_class = SubjectPeriodTransitionPolicy

    def __init__(
        self,
        *,
        repository=None,
        transition_policy=None,
        pending_data_snapshot_reader=None,
    ):
        self.repository = repository or self.repository_class()
        self.transition_policy = transition_policy or self.transition_policy_class()
        self.pending_data_snapshot_reader = (
            pending_data_snapshot_reader or _default_pending_data_snapshot_reader
        )

    def get_availability(
        self,
        *,
        subject_id: int,
    ) -> SubjectPeriodOverrideAvailability:
        lifecycle_status = self.repository.get_subject_lifecycle_status(
            subject_id=subject_id,
        )
        if lifecycle_status != SubjectLifecycleStatusChoices.ACTIVE:
            return SubjectPeriodOverrideAvailability(available=False)
        context = self.repository.get_manual_override_context(
            subject_id=subject_id,
        )
        if context is None:
            return SubjectPeriodOverrideAvailability(available=False)
        return SubjectPeriodOverrideAvailability(
            available=True,
            current_period_no=context.current_period.period_no,
            current_treatment_code=context.current_period.treatment_code,
            current_status=context.current_period.status,
            next_period_no=context.next_period.period_no,
            next_treatment_code=context.next_period.treatment_code,
            source_event_status=context.source_event_status or "",
        )

    @transaction.atomic
    def advance_to_next_period(
        self,
        *,
        study_id: int,
        subject_id: int,
        actor_user_id: int | None,
        period_end_at,
        next_period_start_at,
        reason_code: str,
        reason_text: str,
        pending_data_acknowledged: bool,
        clinical_transition_confirmed: bool,
    ) -> SubjectPeriodOverrideResult:
        reason_code = str(reason_code or "").strip().lower()
        reason_text = str(reason_text or "").strip()
        now = self.repository.now()
        validation_reason = self._validate_request(
            period_end_at=period_end_at,
            next_period_start_at=next_period_start_at,
            reason_code=reason_code,
            reason_text=reason_text,
            pending_data_acknowledged=pending_data_acknowledged,
            clinical_transition_confirmed=clinical_transition_confirmed,
            now=now,
        )
        if validation_reason:
            return SubjectPeriodOverrideResult(
                applied=False,
                reason=validation_reason,
            )

        lifecycle_status = self.repository.get_subject_lifecycle_status_for_update(
            study_id=study_id,
            subject_id=subject_id,
        )
        if lifecycle_status is None:
            return SubjectPeriodOverrideResult(
                applied=False,
                reason="subject_not_found",
            )
        if lifecycle_status != SubjectLifecycleStatusChoices.ACTIVE:
            return SubjectPeriodOverrideResult(
                applied=False,
                reason="subject_lifecycle_not_active",
            )

        periods = self.repository.list_periods_for_update(subject_id=subject_id)
        current_index = self._find_current_period_index(periods)
        if current_index is None or current_index + 1 >= len(periods):
            return SubjectPeriodOverrideResult(
                applied=False,
                reason="next_period_not_available",
            )
        current_period = periods[current_index]
        next_period = periods[current_index + 1]
        decision = self.transition_policy.override_advance_to_next_period(
            current_status=current_period.status,
            next_status=next_period.status,
        )
        if decision is None:
            return SubjectPeriodOverrideResult(
                applied=False,
                reason="period_transition_not_allowed",
                current_period_no=current_period.period_no,
                next_period_no=next_period.period_no,
            )
        if self._washout_not_satisfied(
            current_period=current_period,
            period_end_at=period_end_at,
            next_period_start_at=next_period_start_at,
        ):
            return SubjectPeriodOverrideResult(
                applied=False,
                reason="washout_not_satisfied",
                current_period_no=current_period.period_no,
                next_period_no=next_period.period_no,
            )

        source_event_status = self.repository.get_event_status(
            event_instance_id=current_period.end_event_instance_id,
        )
        period_events = self.repository.list_period_event_snapshots(
            period=current_period,
        )
        pending_data_snapshot = self.pending_data_snapshot_reader(
            subject_id=subject_id,
            event_instances=tuple(
                {
                    "event_instance_id": event.event_instance_id,
                    "event_definition_id": event.event_definition_id,
                    "event_code": event.event_code,
                    "event_status": event.event_status,
                    "sequence_no": event.sequence_no,
                }
                for event in period_events
            ),
        )
        pending_data_snapshot["period_context"] = {
            "current_period_no": current_period.period_no,
            "current_period_status": current_period.status,
            "end_event_instance_id": current_period.end_event_instance_id,
            "end_event_status": source_event_status,
            "next_period_no": next_period.period_no,
            "next_period_status": next_period.status,
        }
        override_id = self.repository.create_transition_override(
            subject_id=subject_id,
            current_period=current_period,
            next_period=next_period,
            period_end_at=period_end_at,
            next_period_start_at=next_period_start_at,
            reason_code=reason_code,
            reason_text=reason_text,
            pending_data_acknowledged=pending_data_acknowledged,
            clinical_transition_confirmed=clinical_transition_confirmed,
            source_event_status=source_event_status,
            pending_data_snapshot=pending_data_snapshot,
            actor_user_id=actor_user_id,
            now=now,
        )
        facts = {
            **pending_data_snapshot["period_context"],
            "pending_form_count": pending_data_snapshot.get(
                "pending_form_count",
                0,
            ),
            "override_id": override_id,
            "period_end_at": period_end_at,
            "next_period_start_at": next_period_start_at,
            "pending_data_acknowledged": pending_data_acknowledged,
            "clinical_transition_confirmed": clinical_transition_confirmed,
        }
        self.repository.record_period_end(
            period=current_period,
            source_event_instance_id=current_period.end_event_instance_id,
            occurred_at=period_end_at,
            actor_user_id=actor_user_id,
        )
        if current_period.washout_days:
            self.repository.record_washout_end(
                period=current_period,
                source_event_instance_id=current_period.end_event_instance_id,
                occurred_at=next_period_start_at,
                actor_user_id=actor_user_id,
            )
        self.repository.transition_period(
            period=current_period,
            to_status=decision.current_status,
            source_event_instance_id=current_period.end_event_instance_id,
            trigger_source="manual_period_override",
            reason=decision.reason,
            facts=facts,
            actor_user_id=actor_user_id,
            now=now,
        )
        updated_next_period = self.repository.transition_period(
            period=next_period,
            to_status=decision.next_status,
            source_event_instance_id=current_period.end_event_instance_id,
            trigger_source="manual_period_override",
            reason=decision.reason,
            facts=facts,
            actor_user_id=actor_user_id,
            now=now,
        )
        self.repository.record_period_start(
            period=updated_next_period,
            source_event_instance_id=current_period.end_event_instance_id,
            occurred_at=next_period_start_at,
            actor_user_id=actor_user_id,
        )
        return SubjectPeriodOverrideResult(
            applied=True,
            reason=decision.reason,
            override_id=override_id,
            current_period_no=current_period.period_no,
            next_period_no=next_period.period_no,
        )

    @staticmethod
    def _validate_request(
        *,
        period_end_at,
        next_period_start_at,
        reason_code,
        reason_text,
        pending_data_acknowledged,
        clinical_transition_confirmed,
        now,
    ) -> str:
        if not SubjectPeriodOverrideReason.is_valid(reason_code) or not reason_text:
            return "override_reason_required"
        if not pending_data_acknowledged:
            return "pending_data_acknowledgement_required"
        if not clinical_transition_confirmed:
            return "clinical_transition_confirmation_required"
        if period_end_at is None or next_period_start_at is None:
            return "transition_dates_required"
        if next_period_start_at < period_end_at:
            return "next_period_start_before_period_end"
        if period_end_at > now or next_period_start_at > now:
            return "transition_date_in_future"
        return ""

    @staticmethod
    def _find_current_period_index(periods) -> int | None:
        return next(
            (
                index
                for index, period in enumerate(periods)
                if SubjectPeriodStatus.normalize(period.status)
                in {
                    SubjectPeriodStatus.ACTIVE,
                    SubjectPeriodStatus.WASHOUT,
                }
            ),
            None,
        )

    @staticmethod
    def _washout_not_satisfied(
        *,
        current_period,
        period_end_at,
        next_period_start_at,
    ) -> bool:
        washout_days = current_period.washout_days or 0
        return next_period_start_at < period_end_at + timedelta(days=washout_days)


__all__ = [
    "SubjectPeriodOverrideAvailability",
    "SubjectPeriodOverrideResult",
    "SubjectPeriodOverrideService",
]

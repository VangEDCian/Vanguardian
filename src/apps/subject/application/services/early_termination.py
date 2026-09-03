from dataclasses import dataclass

from django.db import transaction

from apps.core.choices import (
    EventInstanceStatusChoices,
    SubjectLifecycleStatusChoices,
)
from apps.subject.application.commands import TriggerSubjectEventTransitionCommand
from apps.subject.application.services.event_lifecycle import SubjectEventTransitionService
from apps.subject.infrastructure.repositories.early_termination import (
    DjangoSubjectEarlyTerminationRepository,
)


@dataclass(frozen=True)
class SubjectEarlyTerminationRequestResult:
    requested: bool
    source_event_instance_id: int | None = None
    opened_event_instance_ids: tuple[int, ...] = ()
    skipped_event_count: int = 0
    cancelled_event_count: int = 0
    cancelled_period_count: int = 0
    reason: str = ""


class SubjectEarlyTerminationRequestService:
    repository_class = DjangoSubjectEarlyTerminationRepository
    transition_service_class = SubjectEventTransitionService
    ADOPTABLE_TARGET_STATUSES = (
        EventInstanceStatusChoices.OPEN,
        EventInstanceStatusChoices.IN_PROGRESS,
        EventInstanceStatusChoices.COMPLETED,
        EventInstanceStatusChoices.VERIFIED,
        EventInstanceStatusChoices.LOCKED,
        EventInstanceStatusChoices.FINALIZED,
    )

    def __init__(self, repository=None, transition_service=None):
        self.repository = repository or self.repository_class()
        self.transition_service = transition_service or self.transition_service_class()

    @transaction.atomic
    def request(
        self,
        *,
        study_id: int,
        subject_id: int,
        actor_user_id: int | None,
        effective_at=None,
        reason_code: str = "",
        reason_text: str = "",
    ) -> SubjectEarlyTerminationRequestResult:
        reason_code = str(reason_code or "").strip()
        reason_text = str(reason_text or "").strip()
        if not reason_code or not reason_text:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                reason="termination_reason_required",
            )

        now = self.repository.now()
        effective_at = effective_at or now
        subject = self.repository.get_subject_for_update(
            study_id=study_id,
            subject_id=subject_id,
        )
        if subject is None:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                reason="subject_not_found",
            )
        if (
            subject.lifecycle_status
            == SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
        ):
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                reason="early_termination_already_in_progress",
            )
        if subject.lifecycle_status != SubjectLifecycleStatusChoices.ACTIVE:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                reason="subject_lifecycle_not_active",
            )
        if not subject.is_enrolled:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                reason="subject_not_enrolled",
            )

        eos_event = self.repository.get_reached_regular_eos_event_instance(
            study_id=study_id,
            subject_id=subject_id,
        )
        if eos_event is not None:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                source_event_instance_id=eos_event.id,
                reason="final_visit_already_started",
            )

        transition_context = self.repository.get_early_termination_transition_context(
            study_id=study_id,
            subject_id=subject_id,
        )
        if transition_context is None:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                reason="early_termination_transition_not_available",
            )

        target_event_instance_id = self._open_or_adopt_target(
            transition_context=transition_context,
            actor_user_id=actor_user_id,
        )
        if target_event_instance_id is None:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                source_event_instance_id=transition_context.source_event_instance_id,
                reason="early_termination_transition_not_applied",
            )

        lifecycle_started = self.repository.start_early_termination(
            subject_id=subject_id,
            effective_at=effective_at,
            reason_code=reason_code,
            reason_text=reason_text,
            actor_user_id=actor_user_id,
            now=now,
        )
        if not lifecycle_started:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                source_event_instance_id=transition_context.source_event_instance_id,
                reason="subject_lifecycle_changed",
            )
        skipped_event_count, cancelled_event_count = (
            self.repository.close_other_event_instances(
                subject_id=subject_id,
                early_termination_event_instance_id=target_event_instance_id,
                actor_user_id=actor_user_id,
                now=now,
            )
        )
        cancelled_period_count = self.repository.cancel_open_subject_periods(
            subject_id=subject_id,
            actor_user_id=actor_user_id,
            now=now,
        )
        self.repository.complete_subject_if_early_termination_event(
            event_instance_id=target_event_instance_id,
            actor_user_id=actor_user_id,
            now=now,
        )
        return SubjectEarlyTerminationRequestResult(
            requested=True,
            source_event_instance_id=transition_context.source_event_instance_id,
            opened_event_instance_ids=(target_event_instance_id,),
            skipped_event_count=skipped_event_count,
            cancelled_event_count=cancelled_event_count,
            cancelled_period_count=cancelled_period_count,
            reason="early_termination_started",
        )

    def _open_or_adopt_target(
        self,
        *,
        transition_context,
        actor_user_id: int | None,
    ) -> int | None:
        if (
            transition_context.target_event_instance_id is not None
            and transition_context.target_event_status in self.ADOPTABLE_TARGET_STATUSES
        ):
            return transition_context.target_event_instance_id

        result = self.transition_service.execute(
            TriggerSubjectEventTransitionCommand(
                source_event_instance_id=transition_context.source_event_instance_id,
                facts={"early_termination.requested": True},
                actor_user_id=actor_user_id,
                trigger_source="early_termination",
                target_event_definition_id=transition_context.target_event_definition_id,
            )
        )
        return next(
            (
                applied_event.target_event_instance_id
                for applied_event in result.applied_events
            ),
            None,
        )


class SubjectEarlyTerminationLifecycleService:
    repository_class = DjangoSubjectEarlyTerminationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def complete_if_early_termination_event(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
    ) -> bool:
        return self.repository.complete_subject_if_early_termination_event(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )

    def reopen_if_early_termination_event(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
    ) -> bool:
        return self.repository.reopen_subject_if_early_termination_event(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )


class SubjectCaptureEligibilityService:
    repository_class = DjangoSubjectEarlyTerminationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_eligibility(
        self,
        *,
        subject_id: int,
        event_instance_id: int,
        for_update: bool = False,
    ):
        return self.repository.get_capture_eligibility(
            subject_id=subject_id,
            event_instance_id=event_instance_id,
            for_update=for_update,
        )


class SubjectEarlyTerminationAvailabilityService:
    repository_class = DjangoSubjectEarlyTerminationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def list_eligible_subject_ids(
        self,
        *,
        study_id: int,
        subject_ids: tuple[int, ...],
    ) -> frozenset[int]:
        return self.repository.list_eligible_subject_ids(
            study_id=study_id,
            subject_ids=subject_ids,
        )


__all__ = [
    "SubjectCaptureEligibilityService",
    "SubjectEarlyTerminationAvailabilityService",
    "SubjectEarlyTerminationLifecycleService",
    "SubjectEarlyTerminationRequestResult",
    "SubjectEarlyTerminationRequestService",
]

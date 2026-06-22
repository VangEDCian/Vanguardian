from dataclasses import dataclass

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
    reason: str = ""


class SubjectEarlyTerminationRequestService:
    repository_class = DjangoSubjectEarlyTerminationRepository
    transition_service_class = SubjectEventTransitionService

    def __init__(self, repository=None, transition_service=None):
        self.repository = repository or self.repository_class()
        self.transition_service = transition_service or self.transition_service_class()

    def request(
        self,
        *,
        study_id: int,
        subject_id: int,
        actor_user_id: int | None,
    ) -> SubjectEarlyTerminationRequestResult:
        eos_event = self.repository.get_reached_eos_event_instance(
            study_id=study_id,
            subject_id=subject_id,
        )
        if eos_event is not None:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                source_event_instance_id=eos_event.id,
                reason="final_visit_already_started",
            )

        source_event = self.repository.get_active_visit_event_instance(
            study_id=study_id,
            subject_id=subject_id,
        )
        if source_event is None:
            return SubjectEarlyTerminationRequestResult(
                requested=False,
                reason="active_visit_not_found",
            )

        result = self.transition_service.execute(
            TriggerSubjectEventTransitionCommand(
                source_event_instance_id=source_event.id,
                facts={"early_termination.requested": True},
                actor_user_id=actor_user_id,
                trigger_source="early_termination",
            )
        )
        opened_event_instance_ids = tuple(
            applied_event.target_event_instance_id
            for applied_event in result.applied_events
        )
        if opened_event_instance_ids:
            return SubjectEarlyTerminationRequestResult(
                requested=True,
                source_event_instance_id=source_event.id,
                opened_event_instance_ids=opened_event_instance_ids,
                reason="early_termination_requested",
            )

        skipped_reason = next(
            (skipped.reason for skipped in result.skipped_decisions if skipped.reason),
            "transition_not_applied",
        )
        return SubjectEarlyTerminationRequestResult(
            requested=False,
            source_event_instance_id=source_event.id,
            reason=skipped_reason,
        )


__all__ = [
    "SubjectEarlyTerminationRequestResult",
    "SubjectEarlyTerminationRequestService",
]

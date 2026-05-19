from django.db import transaction

from apps.subject.application.commands import TriggerSubjectEventTransitionCommand
from apps.subject.application.services.event_lifecycle import SubjectEventTransitionService
from apps.subject.infrastructure.repositories import DjangoSubjectEventLifecycleRepository


class SubjectEventCompletionService:
    repository_class = DjangoSubjectEventLifecycleRepository
    transition_service_class = SubjectEventTransitionService

    def __init__(self, repository=None, transition_service=None):
        self.repository = repository or self.repository_class()
        self.transition_service = transition_service or self.transition_service_class(
            repository=self.repository,
        )

    @transaction.atomic
    def complete_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        changed = self.repository.complete_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )
        if changed:
            self._trigger_downstream_transition(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
                trigger_source="subject_event_status_changed",
            )
        return changed

    @transaction.atomic
    def verify_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        changed = self.repository.verify_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )
        if changed:
            self._trigger_downstream_transition(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
                trigger_source="subject_event_status_changed",
            )
        return changed

    @transaction.atomic
    def mark_event_instance_in_progress(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        return self.repository.mark_event_instance_in_progress(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )

    def _trigger_downstream_transition(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        trigger_source: str,
    ) -> None:
        self.transition_service.execute(
            TriggerSubjectEventTransitionCommand(
                source_event_instance_id=event_instance_id,
                facts={},
                actor_user_id=actor_user_id,
                trigger_source=trigger_source,
            )
        )


__all__ = ["SubjectEventCompletionService"]

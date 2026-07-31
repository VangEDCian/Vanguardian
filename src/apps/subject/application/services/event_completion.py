from django.db import transaction

from apps.subject.application.commands import TriggerSubjectEventTransitionCommand
from apps.subject.application.services.early_termination import (
    SubjectEarlyTerminationLifecycleService,
)
from apps.subject.application.services.event_lifecycle import SubjectEventTransitionService
from apps.subject.application.services.period_lifecycle import (
    SubjectPeriodLifecycleService,
)
from apps.subject.infrastructure.repositories import DjangoSubjectEventLifecycleRepository


class SubjectEventCompletionService:
    repository_class = DjangoSubjectEventLifecycleRepository
    early_termination_lifecycle_service_class = (
        SubjectEarlyTerminationLifecycleService
    )
    period_lifecycle_service_class = SubjectPeriodLifecycleService
    transition_service_class = SubjectEventTransitionService

    def __init__(
        self,
        repository=None,
        transition_service=None,
        period_lifecycle_service=None,
        early_termination_lifecycle_service=None,
    ):
        self.repository = repository or self.repository_class()
        self.transition_service = transition_service or self.transition_service_class(
            repository=self.repository,
        )
        self.period_lifecycle_service = (
            period_lifecycle_service or self.period_lifecycle_service_class()
        )
        self.early_termination_lifecycle_service = (
            early_termination_lifecycle_service
            or self.early_termination_lifecycle_service_class()
        )

    @transaction.atomic
    def complete_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        self._lock_subject_for_event_instance(
            event_instance_id=event_instance_id,
        )
        changed = self.repository.complete_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )
        if changed:
            self.early_termination_lifecycle_service.complete_if_early_termination_event(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
            )
            self._update_period_lifecycle(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
            )
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
        self._lock_subject_for_event_instance(
            event_instance_id=event_instance_id,
        )
        changed = self.repository.verify_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )
        if changed:
            self.early_termination_lifecycle_service.complete_if_early_termination_event(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
            )
            self._update_period_lifecycle(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
            )
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
        self._lock_subject_for_event_instance(
            event_instance_id=event_instance_id,
        )
        changed = self.repository.mark_event_instance_in_progress(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )
        if changed:
            self.early_termination_lifecycle_service.reopen_if_early_termination_event(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
            )
            self._update_period_lifecycle(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
                trigger_source="subject_event_reopened",
            )
        return changed

    def _lock_subject_for_event_instance(
        self,
        *,
        event_instance_id: int,
    ) -> None:
        lock_subject = getattr(
            self.repository,
            "lock_subject_for_event_instance",
            None,
        )
        if lock_subject is not None:
            lock_subject(event_instance_id=event_instance_id)

    def _update_period_lifecycle(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        trigger_source: str = "subject_event_status_changed",
    ) -> None:
        self.period_lifecycle_service.handle_event_status_changed(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            trigger_source=trigger_source,
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

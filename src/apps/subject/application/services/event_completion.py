from django.db import transaction

from apps.subject.infrastructure.repositories import DjangoSubjectEventLifecycleRepository


class SubjectEventCompletionService:
    repository_class = DjangoSubjectEventLifecycleRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def complete_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        return self.repository.complete_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )

    @transaction.atomic
    def verify_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        return self.repository.verify_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )

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


__all__ = ["SubjectEventCompletionService"]

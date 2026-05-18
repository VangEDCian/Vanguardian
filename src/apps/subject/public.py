from apps.subject.application import (
    SubjectEventCompletionService,
    SubjectEventInstanceNotFoundError,
    SubjectEventTransitionService,
    TriggerSubjectEventTransitionCommand,
)
from apps.subject.models import Subject, SubjectEventInstance, SubjectEventInstanceFile
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectEventLifecycleAdapter:
    def __init__(self, transition_service=None, completion_service=None):
        self.transition_service = transition_service or SubjectEventTransitionService()
        self.completion_service = completion_service or SubjectEventCompletionService()

    def trigger_event_transition(
        self,
        *,
        source_event_instance_id: int,
        facts=None,
        actor_user_id: int | None = None,
        trigger_source: str = "system",
    ):
        command = TriggerSubjectEventTransitionCommand(
            source_event_instance_id=source_event_instance_id,
            facts=facts or {},
            actor_user_id=actor_user_id,
            trigger_source=trigger_source,
        )
        return self.transition_service.execute(command)

    def complete_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        return self.completion_service.complete_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
        )

    def verify_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        return self.completion_service.verify_event_instance(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
        )

    def mark_event_instance_in_progress(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        return self.completion_service.mark_event_instance_in_progress(
            event_instance_id=event_instance_id,
            actor_user_id=actor_user_id,
        )


def trigger_subject_event_transition(
    *,
    source_event_instance_id: int,
    facts=None,
    actor_user_id: int | None = None,
    trigger_source: str = "system",
):
    return SubjectEventLifecycleAdapter().trigger_event_transition(
        source_event_instance_id=source_event_instance_id,
        facts=facts,
        actor_user_id=actor_user_id,
        trigger_source=trigger_source,
    )


def complete_subject_event_instance(
    *,
    event_instance_id: int,
    actor_user_id: int | None = None,
) -> bool:
    return SubjectEventLifecycleAdapter().complete_event_instance(
        event_instance_id=event_instance_id,
        actor_user_id=actor_user_id,
    )


def verify_subject_event_instance(
    *,
    event_instance_id: int,
    actor_user_id: int | None = None,
) -> bool:
    return SubjectEventLifecycleAdapter().verify_event_instance(
        event_instance_id=event_instance_id,
        actor_user_id=actor_user_id,
    )


def mark_subject_event_instance_in_progress(
    *,
    event_instance_id: int,
    actor_user_id: int | None = None,
) -> bool:
    return SubjectEventLifecycleAdapter().mark_event_instance_in_progress(
        event_instance_id=event_instance_id,
        actor_user_id=actor_user_id,
    )


__all__ = [
    "Subject",
    "SubjectAbstractVerifyStudy",
    "SubjectEventInstance",
    "SubjectEventInstanceFile",
    "SubjectEventInstanceNotFoundError",
    "SubjectEventLifecycleAdapter",
    "complete_subject_event_instance",
    "mark_subject_event_instance_in_progress",
    "trigger_subject_event_transition",
    "verify_subject_event_instance",
]

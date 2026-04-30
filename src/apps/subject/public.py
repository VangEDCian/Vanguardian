from apps.subject.application import (
    SubjectEventInstanceNotFoundError,
    SubjectEventTransitionService,
    TriggerSubjectEventTransitionCommand,
)


class SubjectEventLifecycleAdapter:
    def __init__(self, transition_service=None):
        self.transition_service = transition_service or SubjectEventTransitionService()

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


__all__ = [
    "SubjectEventInstanceNotFoundError",
    "SubjectEventLifecycleAdapter",
    "trigger_subject_event_transition",
]

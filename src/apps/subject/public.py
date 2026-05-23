from apps.subject.application import (
    SubjectEventCompletionService,
    SubjectEventInstanceNotFoundError,
    SubjectEventTransitionService,
    TriggerSubjectEventTransitionCommand,
)
from apps.subject.application.services.eligibility_workflow import (
    SubjectEligibilityWorkflowService,
    SubjectEnrollmentTransitionResult,
    SubjectEventScopeSnapshot,
    SubjectScopeSnapshot,
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


class SubjectEligibilityWorkflowAdapter:
    def __init__(self, workflow_service=None):
        self.workflow_service = workflow_service or SubjectEligibilityWorkflowService()

    def get_subject_scope(self, *, study_id: int, site_id: int, subject_id: int) -> SubjectScopeSnapshot:
        return self.workflow_service.get_subject_scope(
            study_id=study_id,
            site_id=site_id,
            subject_id=subject_id,
        )

    def get_event_scope(self, *, event_instance_id: int) -> SubjectEventScopeSnapshot | None:
        return self.workflow_service.get_event_scope(event_instance_id=event_instance_id)

    def mark_eligible_from_assessment(self, **kwargs) -> SubjectEnrollmentTransitionResult:
        return self.workflow_service.mark_eligible_from_assessment(**kwargs)

    def mark_screen_failure_from_assessment(self, **kwargs) -> SubjectEnrollmentTransitionResult:
        return self.workflow_service.mark_screen_failure_from_assessment(**kwargs)

    def mark_screened_after_retract(self, **kwargs) -> SubjectEnrollmentTransitionResult:
        return self.workflow_service.mark_screened_after_retract(**kwargs)

    def enroll_subject(self, **kwargs) -> SubjectEnrollmentTransitionResult:
        return self.workflow_service.enroll_subject(**kwargs)

    def is_subject_randomized(self, *, study_id: int, subject_id: int) -> bool:
        return self.workflow_service.is_subject_randomized(study_id=study_id, subject_id=subject_id)

    def is_subject_enrolled(self, *, study_id: int, subject_id: int) -> bool:
        return self.workflow_service.is_subject_enrolled(study_id=study_id, subject_id=subject_id)


__all__ = [
    "Subject",
    "SubjectAbstractVerifyStudy",
    "SubjectEventInstance",
    "SubjectEventInstanceFile",
    "SubjectEventInstanceNotFoundError",
    "SubjectEventLifecycleAdapter",
    "SubjectEligibilityWorkflowAdapter",
    "SubjectEnrollmentTransitionResult",
    "SubjectEventScopeSnapshot",
    "SubjectScopeSnapshot",
    "complete_subject_event_instance",
    "mark_subject_event_instance_in_progress",
    "trigger_subject_event_transition",
    "verify_subject_event_instance",
]

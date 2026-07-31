from dataclasses import dataclass

from apps.subject.application.services.period_lifecycle import (
    SubjectPeriodLifecycleService,
)
from apps.subject.application.services.workflow_action import (
    SubjectWorkflowActionService,
)
from apps.subject.infrastructure.repositories import (
    DjangoSubjectPeriodLifecycleRepository,
    DjangoSubjectWorkflowActionRepository,
)


@dataclass(frozen=True)
class SubjectDuePeriodTransitionResult:
    due_subject_count: int
    advanced_subject_count: int
    workflow_event_count: int


class SubjectDuePeriodTransitionService:
    period_repository_class = DjangoSubjectPeriodLifecycleRepository
    workflow_repository_class = DjangoSubjectWorkflowActionRepository
    period_lifecycle_service_class = SubjectPeriodLifecycleService
    workflow_action_service_class = SubjectWorkflowActionService

    def __init__(
        self,
        *,
        period_repository=None,
        workflow_repository=None,
        period_lifecycle_service=None,
        workflow_action_service=None,
    ):
        self.period_repository = period_repository or self.period_repository_class()
        self.workflow_repository = (
            workflow_repository or self.workflow_repository_class()
        )
        self.period_lifecycle_service = (
            period_lifecycle_service or self.period_lifecycle_service_class()
        )
        self.workflow_action_service = (
            workflow_action_service or self.workflow_action_service_class()
        )

    def process_due_transitions(
        self,
        *,
        actor_user_id: int | None = None,
        limit: int = 500,
    ) -> SubjectDuePeriodTransitionResult:
        subject_ids = self.period_repository.list_due_washout_subject_ids(
            as_of=self.period_repository.now(),
            limit=limit,
        )
        event_id_by_subject_id = (
            self.workflow_repository.map_open_washout_event_id_by_subject_id(
                subject_ids=subject_ids,
            )
        )
        advanced_subject_count = 0
        workflow_event_count = 0
        for subject_id in subject_ids:
            event_instance_id = event_id_by_subject_id.get(subject_id)
            if event_instance_id is not None:
                result = self.workflow_action_service.execute_for_open_event(
                    event_instance_id=event_instance_id,
                    actor_user_id=actor_user_id,
                )
                workflow_event_count += int(result.executed)
                advanced_subject_count += int(result.executed)
                continue

            result = self.period_lifecycle_service.advance_after_washout(
                subject_id=subject_id,
                actor_user_id=actor_user_id,
                trigger_source="period_transition_due",
            )
            advanced_subject_count += int(result.has_changes)

        return SubjectDuePeriodTransitionResult(
            due_subject_count=len(subject_ids),
            advanced_subject_count=advanced_subject_count,
            workflow_event_count=workflow_event_count,
        )


__all__ = [
    "SubjectDuePeriodTransitionResult",
    "SubjectDuePeriodTransitionService",
]

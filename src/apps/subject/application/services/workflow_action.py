from dataclasses import dataclass

from django.db import transaction

from apps.study.public import assign_randomization_slot_for_subject
from apps.subject.infrastructure.repositories.workflow_action import (
    DjangoSubjectWorkflowActionRepository,
)

_EVENT_STATUS_OPEN = "open"
_EVENT_TYPE_OPERATIONAL = "operational"
_EXECUTION_MODE_WORKFLOW_ACTION = "workflow_action"
_EVENT_CATEGORY_RANDOMIZATION = "randomization"


@dataclass(frozen=True)
class SubjectWorkflowActionResult:
    event_instance_id: int
    executed: bool = False
    action: str = ""
    reason: str = ""


class SubjectWorkflowActionService:
    repository_class = DjangoSubjectWorkflowActionRepository

    def __init__(self, repository=None, randomization_slot_assigner=None):
        self.repository = repository or self.repository_class()
        self.randomization_slot_assigner = randomization_slot_assigner or assign_randomization_slot_for_subject

    def execute_for_open_event(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
    ) -> SubjectWorkflowActionResult:
        with transaction.atomic():
            event = self.repository.get_event_workflow_context_for_update(event_instance_id=event_instance_id)
            if event is None:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_found")
            if (event.status or "").strip().lower() != _EVENT_STATUS_OPEN:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_open")
            if (event.event_type or "").strip().lower() != _EVENT_TYPE_OPERATIONAL:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_operational")
            if (event.execution_mode or "").strip().lower() != _EXECUTION_MODE_WORKFLOW_ACTION:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_workflow_action")
            if (event.event_category or "").strip().lower() != _EVENT_CATEGORY_RANDOMIZATION:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="unsupported_workflow_action")
            if self.repository.has_subject_randomization(subject_id=event.subject_id):
                return SubjectWorkflowActionResult(
                    event_instance_id=event_instance_id,
                    action=_EVENT_CATEGORY_RANDOMIZATION,
                    reason="subject_already_randomized",
                )

            assignment = self.randomization_slot_assigner(
                study_id=event.study_id,
                subject_id=event.subject_id,
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
            )
            if assignment is None:
                return SubjectWorkflowActionResult(
                    event_instance_id=event_instance_id,
                    action=_EVENT_CATEGORY_RANDOMIZATION,
                    reason="no_available_randomization_slot",
                )

            self.repository.create_subject_randomization(
                study_id=event.study_id,
                site_id=event.site_id,
                subject_id=event.subject_id,
                assignment=assignment,
                actor_user_id=actor_user_id,
                now=self.repository.now(),
            )
            return SubjectWorkflowActionResult(
                event_instance_id=event_instance_id,
                executed=True,
                action=_EVENT_CATEGORY_RANDOMIZATION,
                reason="randomization_assigned",
            )


__all__ = [
    "SubjectWorkflowActionResult",
    "SubjectWorkflowActionService",
]

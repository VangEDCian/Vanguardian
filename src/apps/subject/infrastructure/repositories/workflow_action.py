from dataclasses import dataclass

from django.utils import timezone

from apps.subject.models import SubjectEventInstance, SubjectRandomization


@dataclass(frozen=True)
class SubjectEventWorkflowContext:
    event_instance_id: int
    study_id: int
    subject_id: int
    site_id: int
    status: str
    event_definition_id: int
    event_type: str
    event_category: str
    execution_mode: str


class DjangoSubjectWorkflowActionRepository:
    def now(self):
        return timezone.now()

    def get_event_workflow_context_for_update(self, *, event_instance_id: int) -> SubjectEventWorkflowContext | None:
        event_instance = (
            SubjectEventInstance.objects.select_for_update()
            .select_related("event_definition", "subject")
            .filter(pk=event_instance_id, deleted=False)
            .only(
                "id",
                "study_id",
                "subject_id",
                "status",
                "event_definition_id",
                "event_definition__event_type",
                "event_definition__event_category",
                "event_definition__execution_mode",
                "subject__site_id",
            )
            .first()
        )
        if event_instance is None:
            return None
        return SubjectEventWorkflowContext(
            event_instance_id=event_instance.pk,
            study_id=event_instance.study_id,
            subject_id=event_instance.subject_id,
            site_id=event_instance.subject.site_id,
            status=event_instance.status,
            event_definition_id=event_instance.event_definition_id,
            event_type=event_instance.event_definition.event_type,
            event_category=event_instance.event_definition.event_category or "",
            execution_mode=event_instance.event_definition.execution_mode,
        )

    def has_subject_randomization(self, *, subject_id: int) -> bool:
        return SubjectRandomization.objects.filter(subject_id=subject_id, deleted=False).exists()

    def create_subject_randomization(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
        assignment,
        actor_user_id: int | None,
        now,
    ):
        return SubjectRandomization.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            randomization_status="randomized",
            randomization_datetime=now,
            randomization_sequence=str(assignment.sequence_no),
            randomization_number=str(assignment.sequence_no),
            randomization_source="workflow_action",
            randomized_by_id=actor_user_id,
            subject_id=subject_id,
            site_id=site_id,
            study_id=study_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )


__all__ = [
    "DjangoSubjectWorkflowActionRepository",
    "SubjectEventWorkflowContext",
]

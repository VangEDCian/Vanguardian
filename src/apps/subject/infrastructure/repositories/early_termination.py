from apps.core.choices.study import (
    EventDefinitionCategoryChoices,
    EventDefinitionTypeChoices,
    EventInstanceStatusChoices,
)
from apps.subject.models import SubjectEventInstance


class DjangoSubjectEarlyTerminationRepository:
    EOS_REACHED_STATUSES = (
        EventInstanceStatusChoices.OPEN,
        EventInstanceStatusChoices.IN_PROGRESS,
        EventInstanceStatusChoices.COMPLETED,
        EventInstanceStatusChoices.VERIFIED,
        EventInstanceStatusChoices.LOCKED,
        EventInstanceStatusChoices.FINALIZED,
    )

    def get_active_visit_event_instance(self, *, study_id: int, subject_id: int):
        return (
            SubjectEventInstance.objects.select_related("event_definition")
            .filter(
                study_id=study_id,
                subject_id=subject_id,
                deleted=False,
                status__in=(
                    EventInstanceStatusChoices.OPEN,
                    EventInstanceStatusChoices.IN_PROGRESS,
                ),
                event_definition__deleted=False,
                event_definition__event_type=EventDefinitionTypeChoices.VISIT_BASED,
            )
            .order_by("event_definition__sequence_no", "id")
            .first()
        )

    def get_reached_eos_event_instance(self, *, study_id: int, subject_id: int):
        return (
            SubjectEventInstance.objects.select_related("event_definition")
            .filter(
                study_id=study_id,
                subject_id=subject_id,
                deleted=False,
                status__in=self.EOS_REACHED_STATUSES,
                event_definition__deleted=False,
                event_definition__event_category=EventDefinitionCategoryChoices.EOS,
            )
            .order_by("event_definition__sequence_no", "id")
            .first()
        )


__all__ = ["DjangoSubjectEarlyTerminationRepository"]

from django.db.models import OuterRef, Subquery

from apps.core.choices import EventDefinitionTypeChoices, EventInstanceStatusChoices
from apps.subject.models import SubjectEventInstance


class SubjectListQueryRepository:
    def build_current_visit_subquery(self) -> Subquery:
        return Subquery(
            SubjectEventInstance.objects.filter(
                subject_id=OuterRef("pk"),
                deleted=False,
                status__in=(
                    EventInstanceStatusChoices.OPEN,
                    EventInstanceStatusChoices.IN_PROGRESS,
                ),
                event_definition__event_type=EventDefinitionTypeChoices.VISIT_BASED,
            )
            .order_by("-id")
            .values("event_definition__name")[:1]
        )

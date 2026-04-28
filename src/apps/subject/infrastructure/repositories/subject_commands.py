from django.db.models import Max
from django.utils import timezone

from apps.study.models import EventDefinition, EventTransitionRule, Study
from apps.subject.models import Subject, SubjectEventInstance


class DjangoSubjectCommandRepository:
    def now(self):
        return timezone.now()

    def get_study_for_update(self, *, study_id):
        return (
            Study.objects.select_for_update()
            .filter(pk=study_id, deleted=False)
            .only("id", "code")
            .first()
        )

    def get_next_subject_sequence(self, *, study_id):
        max_current_sequence = Subject.objects.filter(study_id=study_id).aggregate(
            max_current_sequence=Max("current_sequence"),
        )["max_current_sequence"] or 0
        return max_current_sequence + 1

    def create_subject(
        self,
        *,
        subject_code,
        screening_code,
        current_sequence,
        site_id,
        study_id,
        actor_user_id,
        now,
    ):
        return Subject.objects.create(
            subject_code=subject_code,
            screening_code=screening_code,
            current_sequence=current_sequence,
            site_id=site_id,
            study_id=study_id,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    def list_enabled_event_definitions(self, *, study_id):
        return list(
            EventDefinition.objects.filter(
                study_id=study_id,
                deleted=False,
                is_enabled=True,
            )
            .only("id", "study_version", "code", "name", "event_type", "sequence_no")
            .order_by("sequence_no", "id")
        )

    def list_enabled_transition_rules(self, *, study_id, event_definition_ids):
        return list(
            EventTransitionRule.objects.filter(
                study_id=study_id,
                deleted=False,
                is_enabled=True,
                to_event_definition_id__in=event_definition_ids,
            )
            .only(
                "to_event_definition_id",
                "from_event_definition_id",
                "requires_previous_completion",
                "condition_code",
                "condition_expression",
            )
            .order_by("display_order", "id")
        )

    def bulk_create_event_instances(self, event_instances):
        SubjectEventInstance.objects.bulk_create(event_instances)

    def build_event_instance(self, **kwargs):
        return SubjectEventInstance(**kwargs)

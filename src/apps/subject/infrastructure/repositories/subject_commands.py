from django.db.models import Max
from django.utils import timezone

from apps.study.models import EventDefinition, EventTransitionRule, Study
from apps.subject.models import Subject, SubjectEventInstance, SubjectEventInstanceTransitionLog


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
            .select_related("condition_definition")
            .only(
                "to_event_definition_id",
                "from_event_definition_id",
                "requires_previous_completion",
                "condition_code",
                "condition_definition_id",
                "condition_definition__code",
                "offset_days",
            )
            .order_by("display_order", "id")
        )

    def bulk_create_event_instances(self, event_instances):
        event_instances = list(event_instances)
        if not event_instances:
            return

        SubjectEventInstance.objects.bulk_create(event_instances)
        self._bulk_create_initial_event_instance_transition_logs(event_instances=event_instances)

    def list_open_event_instance_ids_for_subject(self, *, subject_id):
        return list(
            SubjectEventInstance.objects.filter(
                subject_id=subject_id,
                deleted=False,
                status="open",
            ).values_list("id", flat=True)
        )

    def build_event_instance(self, **kwargs):
        return SubjectEventInstance(**kwargs)

    def _bulk_create_initial_event_instance_transition_logs(self, *, event_instances):
        event_key_to_initial_instance = {
            (
                event_instance.subject_id,
                event_instance.event_definition_id,
                event_instance.repeat_index,
            ): event_instance
            for event_instance in event_instances
        }
        subject_ids = {event_instance.subject_id for event_instance in event_instances}
        event_definition_ids = {
            event_instance.event_definition_id for event_instance in event_instances
        }
        repeat_indexes = {event_instance.repeat_index for event_instance in event_instances}
        persisted_event_instances = SubjectEventInstance.objects.filter(
            subject_id__in=subject_ids,
            event_definition_id__in=event_definition_ids,
            repeat_index__in=repeat_indexes,
            deleted=False,
        ).only(
            "id",
            "study_id",
            "subject_id",
            "event_definition_id",
            "repeat_index",
            "status",
            "created_at",
            "created_by_id",
        )

        transition_logs = []
        for persisted_event_instance in persisted_event_instances:
            initial_event_instance = event_key_to_initial_instance.get(
                (
                    persisted_event_instance.subject_id,
                    persisted_event_instance.event_definition_id,
                    persisted_event_instance.repeat_index,
                )
            )
            if initial_event_instance is None:
                continue
            transition_logs.append(
                SubjectEventInstanceTransitionLog(
                    study_id=persisted_event_instance.study_id,
                    subject_id=persisted_event_instance.subject_id,
                    source_event_instance_id=persisted_event_instance.pk,
                    target_event_instance_id=None,
                    transition_rule_id=None,
                    from_event_definition_id=persisted_event_instance.event_definition_id,
                    to_event_definition_id=None,
                    from_status="not_created",
                    to_status=persisted_event_instance.status,
                    trigger_source="subject_created",
                    result="applied",
                    reason="initial_event_instance_created",
                    facts_json="{}",
                    created_at=initial_event_instance.created_at,
                    updated_at=initial_event_instance.created_at,
                    created_by_id=initial_event_instance.created_by_id,
                    updated_by_id=initial_event_instance.created_by_id,
                )
            )
        if transition_logs:
            SubjectEventInstanceTransitionLog.objects.bulk_create(transition_logs)

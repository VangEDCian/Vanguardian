from dataclasses import dataclass

from django.db.models import Max
from django.utils import timezone

from apps.core.choices import EventInstanceStatusChoices
from apps.study.models import EventDefinition
from apps.subject.models import Subject, SubjectEventInstance, SubjectEventInstanceTransitionLog


@dataclass(frozen=True)
class SubjectSnapshot:
    id: int
    study_id: int


@dataclass(frozen=True)
class RepeatingEventDefinitionSnapshot:
    id: int
    study_id: int
    study_version: str
    code: str
    name: str
    event_type: str
    max_repeats: int | None


@dataclass(frozen=True)
class SubjectEventInstanceSummary:
    id: int
    status: str
    repeat_index: int


@dataclass(frozen=True)
class CreatedRepeatingEventInstanceSnapshot:
    id: int
    event_definition_id: int
    event_name: str
    repeat_index: int
    status: str


class DjangoSubjectRepeatingEventInstanceRepository:
    def now(self):
        return timezone.now()

    def get_subject_for_update(self, *, study_id: int, subject_id: int) -> SubjectSnapshot | None:
        subject = (
            Subject.objects.select_for_update()
            .filter(pk=subject_id, study_id=study_id, deleted=False)
            .only("id", "study_id")
            .first()
        )
        if subject is None:
            return None
        return SubjectSnapshot(id=subject.pk, study_id=subject.study_id)

    def get_repeating_event_definition_for_update(
        self,
        *,
        study_id: int,
        event_definition_id: int,
    ) -> RepeatingEventDefinitionSnapshot | None:
        event_definition = (
            EventDefinition.objects.select_for_update()
            .filter(
                pk=event_definition_id,
                study_id=study_id,
                deleted=False,
                is_enabled=True,
                is_repeating=True,
            )
            .only(
                "id",
                "study_id",
                "study_version",
                "code",
                "name",
                "event_type",
                "max_repeats",
            )
            .first()
        )
        if event_definition is None:
            return None
        return RepeatingEventDefinitionSnapshot(
            id=event_definition.pk,
            study_id=event_definition.study_id,
            study_version=event_definition.study_version,
            code=event_definition.code,
            name=event_definition.name,
            event_type=event_definition.event_type,
            max_repeats=event_definition.max_repeats,
        )

    def list_event_instances_for_update(
        self,
        *,
        subject_id: int,
        event_definition_id: int,
    ) -> list[SubjectEventInstanceSummary]:
        event_instances = (
            SubjectEventInstance.objects.select_for_update()
            .filter(
                subject_id=subject_id,
                event_definition_id=event_definition_id,
                deleted=False,
            )
            .only("id", "status", "repeat_index")
            .order_by("repeat_index", "id")
        )
        return [
            SubjectEventInstanceSummary(
                id=event_instance.pk,
                status=event_instance.status,
                repeat_index=event_instance.repeat_index,
            )
            for event_instance in event_instances
        ]

    def get_next_repeat_index(self, *, subject_id: int, event_definition_id: int) -> int:
        max_repeat_index = (
            SubjectEventInstance.objects.filter(
                subject_id=subject_id,
                event_definition_id=event_definition_id,
                deleted=False,
            )
            .aggregate(max_repeat_index=Max("repeat_index"))
            .get("max_repeat_index")
        )
        return int(max_repeat_index or 0) + 1

    def create_open_repeating_event_instance(
        self,
        *,
        subject: SubjectSnapshot,
        event_definition: RepeatingEventDefinitionSnapshot,
        repeat_index: int,
        actor_user_id: int | None,
        now,
    ) -> CreatedRepeatingEventInstanceSnapshot:
        event_instance = SubjectEventInstance.objects.create(
            study_id=subject.study_id,
            subject_id=subject.id,
            event_definition_id=event_definition.id,
            study_version=event_definition.study_version,
            repeat_index=repeat_index,
            planned_date=now,
            status=EventInstanceStatusChoices.OPEN,
            opened_at=now,
            opened_by_id=actor_user_id,
            event_code_snapshot=event_definition.code,
            event_name_snapshot=event_definition.name,
            event_type_snapshot=event_definition.event_type,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        SubjectEventInstanceTransitionLog.objects.create(
            study_id=subject.study_id,
            subject_id=subject.id,
            source_event_instance_id=event_instance.pk,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=event_definition.id,
            to_event_definition_id=None,
            from_status="not_created",
            to_status=EventInstanceStatusChoices.OPEN,
            trigger_source="add_repeating_event_instance",
            result="applied",
            reason="repeating_event_instance_created",
            facts_json="{}",
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        return CreatedRepeatingEventInstanceSnapshot(
            id=event_instance.pk,
            event_definition_id=event_definition.id,
            event_name=event_definition.name,
            repeat_index=repeat_index,
            status=event_instance.status,
        )


__all__ = [
    "CreatedRepeatingEventInstanceSnapshot",
    "DjangoSubjectRepeatingEventInstanceRepository",
    "RepeatingEventDefinitionSnapshot",
    "SubjectEventInstanceSummary",
    "SubjectSnapshot",
]

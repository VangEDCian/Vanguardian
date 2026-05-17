import json

from django.utils import timezone

from apps.core.choices import EventInstanceStatusChoices
from apps.study.models import EventDefinition, EventTransitionRule
from apps.subject.domain import (
    StudyEventDefinitionSnapshot,
    StudyEventTransitionRuleSnapshot,
    SubjectEventInstanceSnapshot,
)
from apps.subject.models import SubjectEventInstance, SubjectEventInstanceTransitionLog


class DjangoSubjectEventLifecycleRepository:
    def now(self):
        return timezone.now()

    def get_event_instance_for_update(
        self,
        *,
        event_instance_id: int,
    ) -> SubjectEventInstanceSnapshot | None:
        event_instance = (
            SubjectEventInstance.objects.select_for_update()
            .filter(pk=event_instance_id, deleted=False)
            .only(
                "id",
                "study_id",
                "subject_id",
                "event_definition_id",
                "study_version",
                "repeat_index",
                "status",
                "event_code_snapshot",
                "event_name_snapshot",
                "event_type_snapshot",
            )
            .first()
        )
        if event_instance is None:
            return None
        return self._to_event_instance_snapshot(event_instance)

    def list_enabled_transition_rules_from(
        self,
        *,
        study_id: int,
        study_version: str,
        from_event_definition_id: int,
    ) -> list[StudyEventTransitionRuleSnapshot]:
        transition_rules = (
            EventTransitionRule.objects.filter(
                study_id=study_id,
                study_version=study_version,
                from_event_definition_id=from_event_definition_id,
                deleted=False,
                is_enabled=True,
            )
            .only(
                "id",
                "from_event_definition_id",
                "to_event_definition_id",
                "transition_type",
                "condition_scope",
                "condition_code",
                "condition_expression",
                "auto_open",
                "auto_create",
                "requires_previous_completion",
                "allow_skip",
                "display_order",
            )
            .order_by("display_order", "id")
        )
        return [self._to_transition_rule_snapshot(rule) for rule in transition_rules]

    def list_event_instances_for_update(
        self,
        *,
        subject_id: int,
        event_definition_ids: list[int],
    ) -> dict[int, SubjectEventInstanceSnapshot]:
        if not event_definition_ids:
            return {}

        event_instances = (
            SubjectEventInstance.objects.select_for_update()
            .filter(
                subject_id=subject_id,
                event_definition_id__in=event_definition_ids,
                repeat_index=1,
                deleted=False,
            )
            .only(
                "id",
                "study_id",
                "subject_id",
                "event_definition_id",
                "study_version",
                "repeat_index",
                "status",
                "event_code_snapshot",
                "event_name_snapshot",
                "event_type_snapshot",
            )
        )
        return {
            event_instance.event_definition_id: self._to_event_instance_snapshot(event_instance)
            for event_instance in event_instances
        }

    def get_event_definition(
        self,
        *,
        event_definition_id: int,
    ) -> StudyEventDefinitionSnapshot | None:
        event_definition = (
            EventDefinition.objects.filter(
                pk=event_definition_id,
                deleted=False,
                is_enabled=True,
            )
            .only("id", "study_id", "study_version", "code", "name", "event_type")
            .first()
        )
        if event_definition is None:
            return None
        return StudyEventDefinitionSnapshot(
            id=event_definition.pk,
            study_id=event_definition.study_id,
            study_version=event_definition.study_version,
            code=event_definition.code,
            name=event_definition.name,
            event_type=event_definition.event_type,
        )

    def open_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> SubjectEventInstanceSnapshot | None:
        updated_count = SubjectEventInstance.objects.filter(
            pk=event_instance_id,
            deleted=False,
            status__in=[
                EventInstanceStatusChoices.NOT_READY,
                EventInstanceStatusChoices.PLANNED,
            ],
        ).update(
            status=EventInstanceStatusChoices.OPEN,
            opened_at=now,
            opened_by_id=actor_user_id,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        if updated_count == 0:
            return None
        return self.get_event_instance_for_update(event_instance_id=event_instance_id)

    def create_open_event_instance(
        self,
        *,
        subject_id: int,
        study_id: int,
        event_definition: StudyEventDefinitionSnapshot,
        actor_user_id: int | None,
        now,
    ) -> SubjectEventInstanceSnapshot:
        event_instance = SubjectEventInstance.objects.create(
            study_id=study_id,
            subject_id=subject_id,
            event_definition_id=event_definition.id,
            study_version=event_definition.study_version,
            repeat_index=1,
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
        return self._to_event_instance_snapshot(event_instance)

    def record_transition_log(
        self,
        *,
        study_id: int,
        subject_id: int,
        source_event_instance_id: int,
        target_event_instance_id: int | None,
        transition_rule_id: int | None,
        from_event_definition_id: int,
        to_event_definition_id: int | None,
        from_status: str,
        to_status: str,
        trigger_source: str,
        result: str,
        reason: str | None,
        facts: dict,
        actor_user_id: int | None,
        now,
    ):
        return SubjectEventInstanceTransitionLog.objects.create(
            study_id=study_id,
            subject_id=subject_id,
            source_event_instance_id=source_event_instance_id,
            target_event_instance_id=target_event_instance_id,
            transition_rule_id=transition_rule_id,
            from_event_definition_id=from_event_definition_id,
            to_event_definition_id=to_event_definition_id,
            from_status=from_status,
            to_status=to_status,
            trigger_source=trigger_source,
            result=result,
            reason=reason,
            facts_json=self._serialize_facts(facts),
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    @staticmethod
    def _to_event_instance_snapshot(event_instance) -> SubjectEventInstanceSnapshot:
        return SubjectEventInstanceSnapshot(
            id=event_instance.pk,
            study_id=event_instance.study_id,
            subject_id=event_instance.subject_id,
            event_definition_id=event_instance.event_definition_id,
            study_version=event_instance.study_version,
            repeat_index=event_instance.repeat_index,
            status=event_instance.status,
            event_code=event_instance.event_code_snapshot,
            event_name=event_instance.event_name_snapshot,
            event_type=event_instance.event_type_snapshot,
        )

    @staticmethod
    def _to_transition_rule_snapshot(rule) -> StudyEventTransitionRuleSnapshot:
        return StudyEventTransitionRuleSnapshot(
            id=rule.pk,
            from_event_definition_id=rule.from_event_definition_id,
            to_event_definition_id=rule.to_event_definition_id,
            transition_type=rule.transition_type,
            condition_scope=rule.condition_scope,
            condition_code=rule.condition_code,
            condition_expression=rule.condition_expression,
            auto_open=rule.auto_open,
            auto_create=rule.auto_create,
            requires_previous_completion=rule.requires_previous_completion,
            allow_skip=rule.allow_skip,
            display_order=rule.display_order,
        )

    @staticmethod
    def _serialize_facts(facts: dict) -> str:
        return json.dumps(facts or {}, ensure_ascii=True, default=str, sort_keys=True)


__all__ = ["DjangoSubjectEventLifecycleRepository"]

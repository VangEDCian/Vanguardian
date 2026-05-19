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
            .select_related("condition_definition")
            .only(
                "id",
                "from_event_definition_id",
                "to_event_definition_id",
                "transition_type",
                "condition_scope",
                "condition_code",
                "condition_definition_id",
                "condition_definition__code",
                "auto_open",
                "auto_create",
                "requires_previous_completion",
                "allow_skip",
                "display_order",
                "offset_days",
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
        event_instance = self._get_event_instance_model_for_status_update(
            event_instance_id=event_instance_id,
            allowed_statuses=[
                EventInstanceStatusChoices.NOT_READY,
                EventInstanceStatusChoices.PLANNED,
            ],
        )
        if event_instance is None:
            return None

        from_status = event_instance.status
        SubjectEventInstance.objects.filter(pk=event_instance.pk).update(
            status=EventInstanceStatusChoices.OPEN,
            opened_at=now,
            opened_by_id=actor_user_id,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        self._record_event_instance_status_transition(
            event_instance=event_instance,
            from_status=from_status,
            to_status=EventInstanceStatusChoices.OPEN,
            trigger_source="subject_event_open",
            reason="event_opened",
            facts={},
            actor_user_id=actor_user_id,
            now=now,
        )
        return self.get_event_instance_for_update(event_instance_id=event_instance_id)

    def complete_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> bool:
        event_instance = self._get_event_instance_model_for_status_update(
            event_instance_id=event_instance_id,
            allowed_statuses=[
                EventInstanceStatusChoices.OPEN,
                EventInstanceStatusChoices.IN_PROGRESS,
            ],
        )
        if event_instance is None:
            return False

        from_status = event_instance.status
        SubjectEventInstance.objects.filter(pk=event_instance.pk).update(
            status=EventInstanceStatusChoices.COMPLETED,
            completed_at=now,
            completed_by_id=actor_user_id,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        self._record_event_instance_status_transition(
            event_instance=event_instance,
            from_status=from_status,
            to_status=EventInstanceStatusChoices.COMPLETED,
            trigger_source="datacapture_submit",
            reason="all_visit_forms_submitted",
            facts={},
            actor_user_id=actor_user_id,
            now=now,
        )
        return True

    def mark_event_instance_in_progress(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> bool:
        event_instance = self._get_event_instance_model_for_status_update(
            event_instance_id=event_instance_id,
            allowed_statuses=[
                EventInstanceStatusChoices.COMPLETED,
                EventInstanceStatusChoices.VERIFIED,
            ],
        )
        if event_instance is None:
            return False

        from_status = event_instance.status
        SubjectEventInstance.objects.filter(pk=event_instance.pk).update(
            status=EventInstanceStatusChoices.IN_PROGRESS,
            completed_at=None,
            completed_by_id=None,
            verified_at=None,
            verified_by_id=None,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        self._record_event_instance_status_transition(
            event_instance=event_instance,
            from_status=from_status,
            to_status=EventInstanceStatusChoices.IN_PROGRESS,
            trigger_source="reopen_form",
            reason="correction_required",
            facts={},
            actor_user_id=actor_user_id,
            now=now,
        )
        return True

    def verify_event_instance(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> bool:
        event_instance = self._get_event_instance_model_for_status_update(
            event_instance_id=event_instance_id,
            allowed_statuses=[
                EventInstanceStatusChoices.OPEN,
                EventInstanceStatusChoices.IN_PROGRESS,
                EventInstanceStatusChoices.COMPLETED,
            ],
        )
        if event_instance is None:
            return False

        from_status = event_instance.status
        SubjectEventInstance.objects.filter(pk=event_instance.pk).update(
            status=EventInstanceStatusChoices.VERIFIED,
            verified_at=now,
            verified_by_id=actor_user_id,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        self._record_event_instance_status_transition(
            event_instance=event_instance,
            from_status=from_status,
            to_status=EventInstanceStatusChoices.VERIFIED,
            trigger_source="verification",
            reason="all_visit_forms_verified",
            facts={},
            actor_user_id=actor_user_id,
            now=now,
        )
        return True

    def create_open_event_instance(
        self,
        *,
        subject_id: int,
        study_id: int,
        event_definition: StudyEventDefinitionSnapshot,
        actor_user_id: int | None,
        now,
        planned_date=None,
    ) -> SubjectEventInstanceSnapshot:
        event_instance = SubjectEventInstance.objects.create(
            study_id=study_id,
            subject_id=subject_id,
            event_definition_id=event_definition.id,
            study_version=event_definition.study_version,
            repeat_index=1,
            planned_date=planned_date,
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

    def _get_event_instance_model_for_status_update(
        self,
        *,
        event_instance_id: int,
        allowed_statuses: list[str],
    ):
        return (
            SubjectEventInstance.objects.select_for_update()
            .filter(
                pk=event_instance_id,
                deleted=False,
                status__in=allowed_statuses,
            )
            .only(
                "id",
                "study_id",
                "subject_id",
                "event_definition_id",
                "status",
            )
            .first()
        )

    def _record_event_instance_status_transition(
        self,
        *,
        event_instance,
        from_status: str,
        to_status: str,
        trigger_source: str,
        reason: str,
        facts: dict,
        actor_user_id: int | None,
        now,
    ) -> None:
        if from_status == to_status:
            return
        self.record_transition_log(
            study_id=event_instance.study_id,
            subject_id=event_instance.subject_id,
            source_event_instance_id=event_instance.pk,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=event_instance.event_definition_id,
            to_event_definition_id=None,
            from_status=from_status,
            to_status=to_status,
            trigger_source=trigger_source,
            result="applied",
            reason=reason,
            facts=facts,
            actor_user_id=actor_user_id,
            now=now,
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
            condition_code=rule.condition_code or getattr(rule.condition_definition, "code", None),
            condition_definition_id=rule.condition_definition_id,
            auto_open=rule.auto_open,
            auto_create=rule.auto_create,
            requires_previous_completion=rule.requires_previous_completion,
            allow_skip=rule.allow_skip,
            display_order=rule.display_order,
            offset_days=rule.offset_days,
        )

    @staticmethod
    def _serialize_facts(facts: dict) -> str:
        return json.dumps(facts or {}, ensure_ascii=True, default=str, sort_keys=True)


__all__ = ["DjangoSubjectEventLifecycleRepository"]

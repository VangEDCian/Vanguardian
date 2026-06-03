from django.utils import timezone

from apps.core.choices import EventInstanceStatusChoices
from apps.study.models import EventDefinition, EventTransitionRule
from apps.subject.models import Subject, SubjectEnrollment, SubjectEventInstance, SubjectEventInstanceTransitionLog


class DjangoSubjectEventInstanceResyncRepository:
    def now(self):
        return timezone.now()

    def resolve_active_study_version(self, *, study_id: int) -> str | None:
        return (
            EventDefinition.objects.filter(
                study_id=study_id,
                deleted=False,
                is_enabled=True,
            )
            .order_by("-updated_at", "-id")
            .values_list("study_version", flat=True)
            .first()
        )

    def list_enabled_event_definitions(self, *, study_id: int, study_version: str):
        return list(
            EventDefinition.objects.filter(
                study_id=study_id,
                study_version=study_version,
                deleted=False,
                is_enabled=True,
            )
            .only("id", "study_id", "study_version", "code", "name", "event_type", "sequence_no")
            .order_by("sequence_no", "id")
        )

    def list_enabled_transition_rules(self, *, study_id: int, study_version: str, event_definition_ids: list[int]):
        if not event_definition_ids:
            return []
        return list(
            EventTransitionRule.objects.filter(
                study_id=study_id,
                study_version=study_version,
                deleted=False,
                is_enabled=True,
                to_event_definition_id__in=event_definition_ids,
            )
            .select_related("condition_definition")
            .only(
                "to_event_definition_id",
                "from_event_definition_id",
                "auto_open",
                "requires_previous_completion",
                "condition_code",
                "condition_definition_id",
                "condition_definition__code",
                "offset_days",
                "display_order",
            )
            .order_by("display_order", "id")
        )

    def list_subject_ids_for_study_version(self, *, study_id: int, study_version: str) -> list[int]:
        return list(
            SubjectEventInstance.objects.filter(
                study_id=study_id,
                study_version=study_version,
                deleted=False,
            )
            .order_by("subject_id")
            .values_list("subject_id", flat=True)
            .distinct()
        )

    def list_subject_ids_for_study(self, *, study_id: int, subject_ids=None) -> list[int]:
        queryset = Subject.objects.filter(
            study_id=study_id,
            deleted=False,
        )
        if subject_ids is not None:
            queryset = queryset.filter(id__in=subject_ids)
        return list(queryset.order_by("id").values_list("id", flat=True))

    def list_terminal_subject_ids(self, *, study_id: int, subject_ids: list[int]) -> set[int]:
        if not subject_ids:
            return set()
        rows = (
            SubjectEnrollment.objects.filter(
                study_id=study_id,
                subject_id__in=subject_ids,
                deleted=False,
            )
            .values_list("subject_id", "status")
        )
        terminal_statuses = {"withdrawn", "discontinued", "completed", "complete"}
        return {
            subject_id
            for subject_id, status in rows
            if str(status or "").strip().lower() in terminal_statuses
        }

    def list_event_instances_for_subject_version_for_update(
        self,
        *,
        study_id: int,
        subject_id: int,
        study_version: str,
    ) -> dict[int, SubjectEventInstance]:
        event_instances = (
            SubjectEventInstance.objects.select_for_update()
            .filter(
                study_id=study_id,
                subject_id=subject_id,
                study_version=study_version,
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
                "planned_date",
                "target_date",
                "status",
                "opened_at",
                "event_code_snapshot",
                "event_name_snapshot",
                "event_type_snapshot",
            )
        )
        return {event_instance.event_definition_id: event_instance for event_instance in event_instances}

    def list_transition_ready_event_instance_ids(
        self,
        *,
        study_id: int,
        subject_id: int,
        study_version: str,
    ) -> list[int]:
        return list(
            SubjectEventInstance.objects.filter(
                study_id=study_id,
                subject_id=subject_id,
                study_version=study_version,
                repeat_index=1,
                deleted=False,
                status__in=[
                    EventInstanceStatusChoices.COMPLETED,
                    EventInstanceStatusChoices.VERIFIED,
                    EventInstanceStatusChoices.LOCKED,
                    EventInstanceStatusChoices.FINALIZED,
                ],
            )
            .order_by("id")
            .values_list("id", flat=True)
        )

    def create_event_instance(
        self,
        *,
        subject_id: int,
        study_id: int,
        event_definition,
        status: str,
        planned_date,
        actor_user_id: int | None,
        now,
        trigger_source: str,
    ) -> SubjectEventInstance:
        is_open = status == EventInstanceStatusChoices.OPEN
        event_instance = SubjectEventInstance.objects.create(
            study_id=study_id,
            subject_id=subject_id,
            event_definition_id=event_definition.pk,
            study_version=event_definition.study_version,
            repeat_index=1,
            planned_date=planned_date or (now if is_open else None),
            target_date=planned_date,
            status=status,
            opened_at=now if is_open else None,
            opened_by_id=actor_user_id if is_open else None,
            event_code_snapshot=event_definition.code,
            event_name_snapshot=event_definition.name,
            event_type_snapshot=event_definition.event_type,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        self._record_transition_log(
            event_instance=event_instance,
            from_status="not_created",
            to_status=status,
            trigger_source=trigger_source,
            reason="event_instance_resync_created",
            actor_user_id=actor_user_id,
            now=now,
        )
        return event_instance

    def update_event_instance_runtime(
        self,
        *,
        event_instance: SubjectEventInstance,
        event_definition,
        update_snapshot: bool,
        update_schedule: bool,
        planned_date,
        target_date,
        actor_user_id: int | None,
        now,
    ) -> bool:
        updates = {}
        if update_snapshot:
            updates.update(
                {
                    "event_code_snapshot": event_definition.code,
                    "event_name_snapshot": event_definition.name,
                    "event_type_snapshot": event_definition.event_type,
                }
            )
        if update_schedule:
            updates["planned_date"] = planned_date
            updates["target_date"] = target_date
        if not updates:
            return False
        updates["updated_at"] = now
        updates["updated_by_id"] = actor_user_id

        comparison_updates = {
            field_name: value
            for field_name, value in updates.items()
            if field_name not in {"updated_at", "updated_by_id"}
        }
        changed = any(
            getattr(event_instance, field_name) != value
            for field_name, value in comparison_updates.items()
        )
        if not changed:
            return False

        SubjectEventInstance.objects.filter(pk=event_instance.pk).update(**updates)
        return True

    def reset_open_event_instance_for_gate_resync(
        self,
        *,
        event_instance: SubjectEventInstance,
        actor_user_id: int | None,
        now,
        trigger_source: str,
    ) -> bool:
        if event_instance.status != EventInstanceStatusChoices.OPEN:
            return False
        SubjectEventInstance.objects.filter(pk=event_instance.pk).update(
            status=EventInstanceStatusChoices.NOT_READY,
            opened_at=None,
            opened_by_id=None,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        self._record_transition_log(
            event_instance=event_instance,
            from_status=EventInstanceStatusChoices.OPEN,
            to_status=EventInstanceStatusChoices.NOT_READY,
            trigger_source=trigger_source,
            reason="event_instance_resync_gate_reset",
            actor_user_id=actor_user_id,
            now=now,
        )
        return True

    def cancel_event_instance(
        self,
        *,
        event_instance: SubjectEventInstance,
        reason: str,
        actor_user_id: int | None,
        now,
        trigger_source: str,
    ) -> bool:
        from_status = event_instance.status
        if from_status == EventInstanceStatusChoices.CANCELLED:
            return False
        SubjectEventInstance.objects.filter(pk=event_instance.pk).update(
            status=EventInstanceStatusChoices.CANCELLED,
            cancel_reason=reason,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        self._record_transition_log(
            event_instance=event_instance,
            from_status=from_status,
            to_status=EventInstanceStatusChoices.CANCELLED,
            trigger_source=trigger_source,
            reason=reason,
            actor_user_id=actor_user_id,
            now=now,
        )
        return True

    def record_resync_impact(
        self,
        *,
        event_instance: SubjectEventInstance,
        reason: str,
        actor_user_id: int | None,
        now,
        trigger_source: str,
    ) -> None:
        self._record_transition_log(
            event_instance=event_instance,
            from_status=event_instance.status,
            to_status=event_instance.status,
            trigger_source=trigger_source,
            reason=reason,
            actor_user_id=actor_user_id,
            now=now,
            result="warning",
        )

    def _record_transition_log(
        self,
        *,
        event_instance: SubjectEventInstance,
        from_status: str,
        to_status: str,
        trigger_source: str,
        reason: str,
        actor_user_id: int | None,
        now,
        result: str = "applied",
    ) -> None:
        SubjectEventInstanceTransitionLog.objects.create(
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
            result=result,
            reason=reason,
            facts_json="{}",
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )


__all__ = ["DjangoSubjectEventInstanceResyncRepository"]

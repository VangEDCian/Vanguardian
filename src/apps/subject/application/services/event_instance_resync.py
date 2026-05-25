from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction

from apps.subject.domain import SubjectEventInstance
from apps.subject.infrastructure.repositories import DjangoSubjectEventInstanceResyncRepository


@dataclass(frozen=True)
class SubjectEventInstanceResyncResult:
    study_id: int
    study_version: str
    subject_count: int = 0
    event_definition_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_terminal_count: int = 0
    reason: str = ""

    @property
    def has_changes(self) -> bool:
        return self.created_count > 0 or self.updated_count > 0


class SubjectEventInstanceResyncService:
    repository_class = DjangoSubjectEventInstanceResyncRepository
    resyncable_statuses = frozenset(
        {
            SubjectEventInstance.NOT_READY,
            SubjectEventInstance.PLANNED,
        }
    )

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def resync_study_version(
        self,
        *,
        study_id: int,
        study_version: str,
        actor_user_id: int | None = None,
        include_all_subjects: bool = False,
        subject_ids=None,
        trigger_source: str = "study_eventdefinition_resync",
    ) -> SubjectEventInstanceResyncResult:
        normalized_study_version = str(study_version or "").strip()
        if not normalized_study_version:
            return SubjectEventInstanceResyncResult(study_id=study_id, study_version="")

        with transaction.atomic():
            return self._resync_study_version_once(
                study_id=study_id,
                study_version=normalized_study_version,
                actor_user_id=actor_user_id,
                include_all_subjects=include_all_subjects,
                target_subject_ids=self._normalize_subject_ids(subject_ids),
                trigger_source=trigger_source,
            )

    def resync_subject_active_study_version(
        self,
        *,
        study_id: int,
        subject_id: int,
        actor_user_id: int | None = None,
        trigger_source: str = "subject_list_resync_stage",
    ) -> SubjectEventInstanceResyncResult:
        study_version = self.repository.resolve_active_study_version(study_id=study_id)
        if not study_version:
            return SubjectEventInstanceResyncResult(
                study_id=study_id,
                study_version="",
                reason="active_study_version_not_found",
            )
        return self.resync_study_version(
            study_id=study_id,
            study_version=study_version,
            actor_user_id=actor_user_id,
            subject_ids=[subject_id],
            trigger_source=trigger_source,
        )

    def _resync_study_version_once(
        self,
        *,
        study_id: int,
        study_version: str,
        actor_user_id: int | None,
        include_all_subjects: bool,
        target_subject_ids: tuple[int, ...] | None,
        trigger_source: str,
    ) -> SubjectEventInstanceResyncResult:
        event_definitions = self.repository.list_enabled_event_definitions(
            study_id=study_id,
            study_version=study_version,
        )
        if not event_definitions:
            return SubjectEventInstanceResyncResult(
                study_id=study_id,
                study_version=study_version,
                reason="event_definitions_not_found",
            )

        event_definition_ids = [event_definition.pk for event_definition in event_definitions]
        transition_rules = self.repository.list_enabled_transition_rules(
            study_id=study_id,
            study_version=study_version,
            event_definition_ids=event_definition_ids,
        )
        subject_ids = self._resolve_subject_ids(
            study_id=study_id,
            study_version=study_version,
            include_all_subjects=include_all_subjects,
            target_subject_ids=target_subject_ids,
        )
        if not subject_ids:
            return SubjectEventInstanceResyncResult(
                study_id=study_id,
                study_version=study_version,
                event_definition_count=len(event_definitions),
                reason="subjects_not_found",
            )

        now = self.repository.now()
        planned_date_by_event_definition = self._build_planned_date_by_event_definition(
            transition_rules=transition_rules,
            anchor_datetime=now,
        )
        incoming_rules_by_event_definition = self._group_rules_by_target(transition_rules)
        created_count = 0
        updated_count = 0
        skipped_terminal_count = 0

        for subject_id in subject_ids:
            existing_events = self.repository.list_event_instances_for_subject_version_for_update(
                study_id=study_id,
                subject_id=subject_id,
                study_version=study_version,
                event_definition_ids=event_definition_ids,
            )
            status_by_event_definition = {
                event_definition_id: event_instance.status
                for event_definition_id, event_instance in existing_events.items()
            }
            desired_status_by_event_definition = self._resolve_desired_status_by_event_definition(
                event_definitions=event_definitions,
                incoming_rules_by_event_definition=incoming_rules_by_event_definition,
                current_status_by_event_definition=status_by_event_definition,
            )

            for event_definition in event_definitions:
                desired_status = desired_status_by_event_definition.get(
                    event_definition.pk,
                    SubjectEventInstance.NOT_READY,
                )
                planned_date = planned_date_by_event_definition.get(event_definition.pk)
                existing_event = existing_events.get(event_definition.pk)
                if existing_event is None:
                    self.repository.create_event_instance(
                        subject_id=subject_id,
                        study_id=study_id,
                        event_definition=event_definition,
                        status=desired_status,
                        planned_date=planned_date,
                        actor_user_id=actor_user_id,
                        now=now,
                        trigger_source=trigger_source,
                    )
                    created_count += 1
                    continue

                if SubjectEventInstance.is_terminal(existing_event.status):
                    skipped_terminal_count += 1
                    continue

                updated = self.repository.resync_event_instance(
                    event_instance=existing_event,
                    event_definition=event_definition,
                    desired_status=desired_status,
                    planned_date=planned_date,
                    actor_user_id=actor_user_id,
                    now=now,
                    trigger_source=trigger_source,
                    allow_status_change=existing_event.status in self.resyncable_statuses,
                )
                if updated:
                    updated_count += 1

        return SubjectEventInstanceResyncResult(
            study_id=study_id,
            study_version=study_version,
            subject_count=len(subject_ids),
            event_definition_count=len(event_definitions),
            created_count=created_count,
            updated_count=updated_count,
            skipped_terminal_count=skipped_terminal_count,
            reason="completed",
        )

    def _resolve_desired_status_by_event_definition(
        self,
        *,
        event_definitions,
        incoming_rules_by_event_definition,
        current_status_by_event_definition: dict[int, str],
    ) -> dict[int, str]:
        desired_status_by_event_definition = {}
        for event_definition in event_definitions:
            incoming_rules = incoming_rules_by_event_definition.get(event_definition.pk, [])
            if not incoming_rules:
                desired_status_by_event_definition[event_definition.pk] = SubjectEventInstance.OPEN
                continue

            can_auto_open = any(
                self._can_auto_open_rule(
                    transition_rule=transition_rule,
                    current_status_by_event_definition=current_status_by_event_definition,
                )
                for transition_rule in incoming_rules
            )
            desired_status_by_event_definition[event_definition.pk] = (
                SubjectEventInstance.OPEN if can_auto_open else SubjectEventInstance.NOT_READY
            )
        return desired_status_by_event_definition

    @staticmethod
    def _can_auto_open_rule(*, transition_rule, current_status_by_event_definition: dict[int, str]) -> bool:
        if not getattr(transition_rule, "auto_open", True):
            return False

        if getattr(transition_rule, "requires_previous_completion", False):
            from_event_status = current_status_by_event_definition.get(
                transition_rule.from_event_definition_id,
                SubjectEventInstance.NOT_READY,
            )
            if not SubjectEventInstance.is_terminal(from_event_status):
                return False

        condition_code = str(
            getattr(transition_rule, "condition_code", None)
            or getattr(getattr(transition_rule, "condition_definition", None), "code", "")
            or ""
        ).strip()
        return not condition_code

    @staticmethod
    def _group_rules_by_target(transition_rules) -> dict[int, list]:
        rules_by_target: dict[int, list] = {}
        for transition_rule in transition_rules:
            rules_by_target.setdefault(transition_rule.to_event_definition_id, []).append(transition_rule)
        return rules_by_target

    @staticmethod
    def _build_planned_date_by_event_definition(*, transition_rules, anchor_datetime) -> dict[int, object]:
        planned_date_by_event_definition = {}
        for transition_rule in transition_rules:
            offset_days = getattr(transition_rule, "offset_days", None)
            if offset_days is None:
                continue
            planned_date_by_event_definition.setdefault(
                transition_rule.to_event_definition_id,
                anchor_datetime + timedelta(days=offset_days),
            )
        return planned_date_by_event_definition

    def _resolve_subject_ids(
        self,
        *,
        study_id: int,
        study_version: str,
        include_all_subjects: bool,
        target_subject_ids: tuple[int, ...] | None,
    ) -> list[int]:
        if target_subject_ids is not None:
            return self.repository.list_subject_ids_for_study(
                study_id=study_id,
                subject_ids=target_subject_ids,
            )
        if include_all_subjects:
            return self.repository.list_subject_ids_for_study(study_id=study_id)
        return self.repository.list_subject_ids_for_study_version(
            study_id=study_id,
            study_version=study_version,
        )

    @staticmethod
    def _normalize_subject_ids(subject_ids) -> tuple[int, ...] | None:
        if subject_ids is None:
            return None
        normalized_subject_ids = []
        seen_subject_ids = set()
        for subject_id in subject_ids:
            try:
                normalized_subject_id = int(subject_id)
            except (TypeError, ValueError):
                continue
            if normalized_subject_id <= 0 or normalized_subject_id in seen_subject_ids:
                continue
            normalized_subject_ids.append(normalized_subject_id)
            seen_subject_ids.add(normalized_subject_id)
        return tuple(normalized_subject_ids)


__all__ = [
    "SubjectEventInstanceResyncResult",
    "SubjectEventInstanceResyncService",
]

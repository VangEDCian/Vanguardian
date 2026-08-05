import json
from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from apps.core.choices import (
    EventDefinitionCategoryChoices,
    EventDefinitionLifecycleRoleChoices,
    EventDefinitionTimingModeChoices,
    EventInstanceStatusChoices,
    SubjectLifecycleStatusChoices,
    SubjectPeriodStatusChoices,
)
from apps.study.models import EventTransitionRule
from apps.subject.models import (
    Subject,
    SubjectEnrollment,
    SubjectEventInstance,
    SubjectEventInstanceTransitionLog,
    SubjectPeriod,
    SubjectPeriodTransitionLog,
    SubjectStatusHistory,
)


@dataclass(frozen=True)
class SubjectLifecycleSnapshot:
    subject_id: int
    lifecycle_status: str
    is_enrolled: bool


@dataclass(frozen=True)
class EarlyTerminationTransitionContext:
    source_event_instance_id: int
    target_event_definition_id: int
    target_event_instance_id: int | None = None
    target_event_status: str | None = None


@dataclass(frozen=True)
class SubjectCaptureEligibility:
    allowed: bool
    reason: str


class DjangoSubjectEarlyTerminationRepository:
    EARLY_TERMINATION_FACT = "early_termination.requested"
    EOS_REACHED_STATUSES = (
        EventInstanceStatusChoices.IN_PROGRESS,
        EventInstanceStatusChoices.COMPLETED,
        EventInstanceStatusChoices.VERIFIED,
        EventInstanceStatusChoices.LOCKED,
        EventInstanceStatusChoices.FINALIZED,
    )
    ACTIVE_OR_TRANSITION_READY_STATUSES = (
        EventInstanceStatusChoices.OPEN,
        EventInstanceStatusChoices.IN_PROGRESS,
        EventInstanceStatusChoices.COMPLETED,
        EventInstanceStatusChoices.VERIFIED,
        EventInstanceStatusChoices.LOCKED,
        EventInstanceStatusChoices.FINALIZED,
    )
    TRANSITION_READY_STATUSES = (
        EventInstanceStatusChoices.COMPLETED,
        EventInstanceStatusChoices.VERIFIED,
        EventInstanceStatusChoices.LOCKED,
        EventInstanceStatusChoices.FINALIZED,
    )
    EARLY_TERMINATION_COMPLETION_STATUSES = TRANSITION_READY_STATUSES
    INCOMPLETE_EVENT_STATUSES = (
        EventInstanceStatusChoices.NOT_READY,
        EventInstanceStatusChoices.PLANNED,
        EventInstanceStatusChoices.OPEN,
        EventInstanceStatusChoices.IN_PROGRESS,
    )

    def now(self):
        return timezone.now()

    def get_subject_for_update(
        self,
        *,
        study_id: int,
        subject_id: int,
    ) -> SubjectLifecycleSnapshot | None:
        subject = (
            Subject.objects.select_for_update()
            .filter(pk=subject_id, study_id=study_id, deleted=False)
            .only("id", "lifecycle_status")
            .first()
        )
        if subject is None:
            return None
        return SubjectLifecycleSnapshot(
            subject_id=subject.pk,
            lifecycle_status=subject.lifecycle_status,
            is_enrolled=SubjectEnrollment.objects.filter(
                subject_id=subject.pk,
                study_id=study_id,
                deleted=False,
                is_enrolled=True,
            ).exists(),
        )

    def get_early_termination_transition_context(
        self,
        *,
        study_id: int,
        subject_id: int,
    ) -> EarlyTerminationTransitionContext | None:
        transition_rules = (
            self._early_termination_transition_rules(study_id=study_id)
            .select_related(
                "condition_definition",
                "to_event_definition",
            )
            .order_by("display_order", "id")
        )
        for transition_rule in transition_rules:
            allowed_statuses = (
                self.TRANSITION_READY_STATUSES
                if transition_rule.requires_previous_completion
                else self.ACTIVE_OR_TRANSITION_READY_STATUSES
            )
            source_event_instance_id = (
                SubjectEventInstance.objects.filter(
                    study_id=study_id,
                    subject_id=subject_id,
                    study_version=transition_rule.study_version,
                    event_definition_id=transition_rule.from_event_definition_id,
                    deleted=False,
                    status__in=allowed_statuses,
                )
                .order_by("-id")
                .values_list("id", flat=True)
                .first()
            )
            if source_event_instance_id is None:
                continue
            target_event = (
                SubjectEventInstance.objects.filter(
                    study_id=study_id,
                    subject_id=subject_id,
                    study_version=transition_rule.study_version,
                    event_definition_id=transition_rule.to_event_definition_id,
                    repeat_index=1,
                    deleted=False,
                )
                .only("id", "status")
                .first()
            )
            return EarlyTerminationTransitionContext(
                source_event_instance_id=source_event_instance_id,
                target_event_definition_id=transition_rule.to_event_definition_id,
                target_event_instance_id=target_event.pk if target_event else None,
                target_event_status=target_event.status if target_event else None,
            )
        return None

    def get_reached_regular_eos_event_instance(self, *, study_id: int, subject_id: int):
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
            .exclude(
                event_definition__lifecycle_role=(
                    EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION
                )
            )
            .order_by("event_definition__sequence_no", "id")
            .first()
        )

    def start_early_termination(
        self,
        *,
        subject_id: int,
        effective_at,
        reason_code: str,
        reason_text: str,
        actor_user_id: int | None,
        now,
    ) -> bool:
        changed = Subject.objects.filter(
            pk=subject_id,
            lifecycle_status=SubjectLifecycleStatusChoices.ACTIVE,
            deleted=False,
        ).update(
            lifecycle_status=SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
            lifecycle_status_at=effective_at,
            lifecycle_reason_code=reason_code,
            lifecycle_reason_text=reason_text,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        if not changed:
            return False
        SubjectStatusHistory.objects.create(
            subject_id=subject_id,
            from_status=SubjectLifecycleStatusChoices.ACTIVE,
            to_status=SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
            transition_at=effective_at,
            reason_code=reason_code,
            reason_text=reason_text,
            source="user",
            changed_by_id=actor_user_id,
        )
        return True

    def close_other_event_instances(
        self,
        *,
        subject_id: int,
        early_termination_event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> tuple[int, int]:
        event_instances = list(
            SubjectEventInstance.objects.select_for_update()
            .filter(
                subject_id=subject_id,
                deleted=False,
                status__in=self.INCOMPLETE_EVENT_STATUSES,
            )
            .exclude(pk=early_termination_event_instance_id)
            .only("id", "study_id", "subject_id", "event_definition_id", "status")
        )
        skipped_count = 0
        cancelled_count = 0
        for event_instance in event_instances:
            from_status = event_instance.status
            is_future = from_status in (
                EventInstanceStatusChoices.NOT_READY,
                EventInstanceStatusChoices.PLANNED,
            )
            to_status = (
                EventInstanceStatusChoices.SKIPPED
                if is_future
                else EventInstanceStatusChoices.CANCELLED
            )
            update_fields = {
                "status": to_status,
                "updated_at": now,
                "updated_by_id": actor_user_id,
            }
            if is_future:
                update_fields["skip_reason"] = "subject_early_termination"
                skipped_count += 1
            else:
                update_fields["cancel_reason"] = "subject_early_termination"
                cancelled_count += 1
            SubjectEventInstance.objects.filter(pk=event_instance.pk).update(
                **update_fields,
            )
            self._record_event_status_transition(
                event_instance=event_instance,
                from_status=from_status,
                to_status=to_status,
                actor_user_id=actor_user_id,
                now=now,
            )
        return skipped_count, cancelled_count

    def cancel_open_subject_periods(
        self,
        *,
        subject_id: int,
        actor_user_id: int | None,
        now,
    ) -> int:
        periods = list(
            SubjectPeriod.objects.select_for_update()
            .filter(
                subject_id=subject_id,
                deleted=False,
                status__in=(
                    SubjectPeriodStatusChoices.PLANNED,
                    SubjectPeriodStatusChoices.ACTIVE,
                    SubjectPeriodStatusChoices.WASHOUT,
                    SubjectPeriodStatusChoices.REVIEW_REQUIRED,
                ),
            )
            .only("id", "subject_id", "status")
        )
        for period in periods:
            SubjectPeriod.objects.filter(pk=period.pk).update(
                status=SubjectPeriodStatusChoices.CANCELLED,
                updated_at=now,
                updated_by_id=actor_user_id,
            )
            SubjectPeriodTransitionLog.objects.create(
                created_at=now,
                updated_at=now,
                deleted=False,
                period_id=period.pk,
                subject_id=subject_id,
                from_status=period.status,
                to_status=SubjectPeriodStatusChoices.CANCELLED,
                trigger_source="early_termination",
                reason="subject_early_termination",
                facts_json="{}",
                actor_user_id=actor_user_id,
            )
        return len(periods)

    def complete_subject_if_early_termination_event(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> bool:
        event_instance = (
            SubjectEventInstance.objects.select_for_update()
            .select_related("event_definition")
            .filter(
                pk=event_instance_id,
                deleted=False,
                status__in=self.EARLY_TERMINATION_COMPLETION_STATUSES,
                event_definition__deleted=False,
                event_definition__lifecycle_role=(
                    EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION
                ),
            )
            .only("id", "subject_id", "event_definition__lifecycle_role")
            .first()
        )
        if event_instance is None:
            return False
        subject = (
            Subject.objects.select_for_update()
            .filter(
                pk=event_instance.subject_id,
                deleted=False,
                lifecycle_status=(
                    SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
                ),
            )
            .only(
                "id",
                "lifecycle_status",
                "lifecycle_reason_code",
                "lifecycle_reason_text",
            )
            .first()
        )
        if subject is None:
            return False
        Subject.objects.filter(pk=subject.pk).update(
            lifecycle_status=SubjectLifecycleStatusChoices.EARLY_TERMINATED,
            lifecycle_status_at=now,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        SubjectStatusHistory.objects.create(
            subject_id=subject.pk,
            from_status=SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
            to_status=SubjectLifecycleStatusChoices.EARLY_TERMINATED,
            transition_at=now,
            reason_code=subject.lifecycle_reason_code,
            reason_text=subject.lifecycle_reason_text,
            source="system",
            changed_by_id=actor_user_id,
        )
        return True

    def reopen_subject_if_early_termination_event(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None,
        now,
    ) -> bool:
        event_instance = (
            SubjectEventInstance.objects.select_for_update()
            .filter(
                pk=event_instance_id,
                deleted=False,
                status=EventInstanceStatusChoices.IN_PROGRESS,
                event_definition__deleted=False,
                event_definition__lifecycle_role=(
                    EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION
                ),
            )
            .only("id", "subject_id")
            .first()
        )
        if event_instance is None:
            return False
        subject = (
            Subject.objects.select_for_update()
            .filter(
                pk=event_instance.subject_id,
                deleted=False,
                lifecycle_status=SubjectLifecycleStatusChoices.EARLY_TERMINATED,
            )
            .only(
                "id",
                "lifecycle_status",
                "lifecycle_reason_code",
                "lifecycle_reason_text",
            )
            .first()
        )
        if subject is None:
            return False
        Subject.objects.filter(pk=subject.pk).update(
            lifecycle_status=SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
            lifecycle_status_at=now,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        SubjectStatusHistory.objects.create(
            subject_id=subject.pk,
            from_status=SubjectLifecycleStatusChoices.EARLY_TERMINATED,
            to_status=SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
            transition_at=now,
            reason_code=subject.lifecycle_reason_code,
            reason_text=subject.lifecycle_reason_text,
            source="system",
            changed_by_id=actor_user_id,
        )
        return True

    def get_capture_eligibility(
        self,
        *,
        subject_id: int,
        event_instance_id: int,
        for_update: bool = False,
    ) -> SubjectCaptureEligibility:
        subject_queryset = Subject.objects.filter(
            pk=subject_id,
            deleted=False,
        )
        if for_update:
            subject_queryset = subject_queryset.select_for_update()
        lifecycle_status = subject_queryset.values_list(
            "lifecycle_status",
            flat=True,
        ).first()
        if lifecycle_status is None:
            return SubjectCaptureEligibility(False, "subject_not_found")

        event_queryset = SubjectEventInstance.objects.filter(
            pk=event_instance_id,
            subject_id=subject_id,
            deleted=False,
            event_definition__deleted=False,
        )
        if for_update:
            event_queryset = event_queryset.select_for_update()
        lifecycle_role = event_queryset.values_list(
            "event_definition__lifecycle_role",
            flat=True,
        ).first()
        if lifecycle_role is None:
            return SubjectCaptureEligibility(False, "subject_event_not_found")

        if lifecycle_status == SubjectLifecycleStatusChoices.ACTIVE:
            if lifecycle_role == EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION:
                return SubjectCaptureEligibility(
                    False,
                    "early_termination_not_started",
                )
            return SubjectCaptureEligibility(True, "subject_active")
        if (
            lifecycle_status
            == SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
            and lifecycle_role
            == EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION
        ):
            return SubjectCaptureEligibility(True, "early_termination_event")
        return SubjectCaptureEligibility(False, "subject_lifecycle_blocks_capture")

    def is_transition_target_allowed(
        self,
        *,
        subject_id: int,
        event_definition_id: int,
    ) -> bool:
        row = (
            Subject.objects.filter(pk=subject_id, deleted=False)
            .values("lifecycle_status")
            .first()
        )
        if row is None:
            return False
        lifecycle_status = row["lifecycle_status"]
        if lifecycle_status == SubjectLifecycleStatusChoices.ACTIVE:
            return True
        if lifecycle_status != SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS:
            return False
        return SubjectEventInstance.objects.filter(
            subject_id=subject_id,
            event_definition_id=event_definition_id,
            deleted=False,
            event_definition__lifecycle_role=(
                EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION
            ),
        ).exists()

    def list_eligible_subject_ids(
        self,
        *,
        study_id: int,
        subject_ids: tuple[int, ...],
    ) -> frozenset[int]:
        if not subject_ids:
            return frozenset()
        active_subject_ids = set(
            Subject.objects.filter(
                pk__in=subject_ids,
                study_id=study_id,
                deleted=False,
                lifecycle_status=SubjectLifecycleStatusChoices.ACTIVE,
                enrollment__deleted=False,
                enrollment__is_enrolled=True,
            ).values_list("id", flat=True)
        )
        reached_regular_eos_subject_ids = set(
            SubjectEventInstance.objects.filter(
                subject_id__in=active_subject_ids,
                deleted=False,
                status__in=self.EOS_REACHED_STATUSES,
                event_definition__deleted=False,
                event_definition__event_category=EventDefinitionCategoryChoices.EOS,
            )
            .exclude(
                event_definition__lifecycle_role=(
                    EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION
                )
            )
            .values_list("subject_id", flat=True)
        )
        candidate_subject_ids = active_subject_ids - reached_regular_eos_subject_ids
        if not candidate_subject_ids:
            return frozenset()

        eligible_subject_ids: set[int] = set()
        transition_rules = self._early_termination_transition_rules(
            study_id=study_id,
        )
        for rule in transition_rules:
            allowed_statuses = (
                self.TRANSITION_READY_STATUSES
                if rule.requires_previous_completion
                else self.ACTIVE_OR_TRANSITION_READY_STATUSES
            )
            source_subject_ids = set(
                SubjectEventInstance.objects.filter(
                    subject_id__in=candidate_subject_ids,
                    study_version=rule.study_version,
                    event_definition_id=rule.from_event_definition_id,
                    deleted=False,
                    status__in=allowed_statuses,
                ).values_list("subject_id", flat=True)
            )
            if not source_subject_ids:
                continue
            existing_target_subject_ids = set(
                SubjectEventInstance.objects.filter(
                    subject_id__in=source_subject_ids,
                    study_version=rule.study_version,
                    event_definition_id=rule.to_event_definition_id,
                    repeat_index=1,
                    deleted=False,
                    status__in=(
                        EventInstanceStatusChoices.NOT_READY,
                        EventInstanceStatusChoices.PLANNED,
                        *self.ACTIVE_OR_TRANSITION_READY_STATUSES,
                    ),
                ).values_list("subject_id", flat=True)
            )
            if rule.auto_create:
                eligible_subject_ids.update(source_subject_ids)
            else:
                eligible_subject_ids.update(existing_target_subject_ids)
        return frozenset(eligible_subject_ids)

    def _early_termination_transition_rules(self, *, study_id: int):
        # Protocol metadata identifies an Early Termination route. Subject
        # participation eligibility is enforced separately from this query.
        return EventTransitionRule.objects.filter(
            study_id=study_id,
            deleted=False,
            is_enabled=True,
            auto_open=True,
            to_event_definition__deleted=False,
            to_event_definition__event_category=EventDefinitionCategoryChoices.EOS,
            to_event_definition__timing_mode=EventDefinitionTimingModeChoices.CONDITIONAL,
            to_event_definition__lifecycle_role=(
                EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION
            ),
        ).filter(
            Q(condition_code=self.EARLY_TERMINATION_FACT)
            | Q(condition_definition__code=self.EARLY_TERMINATION_FACT)
        )

    @staticmethod
    def _record_event_status_transition(
        *,
        event_instance,
        from_status: str,
        to_status: str,
        actor_user_id: int | None,
        now,
    ) -> None:
        SubjectEventInstanceTransitionLog.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            study_id=event_instance.study_id,
            subject_id=event_instance.subject_id,
            source_event_instance_id=event_instance.pk,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=event_instance.event_definition_id,
            to_event_definition_id=None,
            from_status=from_status,
            to_status=to_status,
            trigger_source="early_termination",
            result="applied",
            reason="subject_early_termination",
            facts_json=json.dumps(
                {"early_termination.requested": True},
                ensure_ascii=True,
                sort_keys=True,
            ),
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )


__all__ = [
    "DjangoSubjectEarlyTerminationRepository",
    "EarlyTerminationTransitionContext",
    "SubjectCaptureEligibility",
    "SubjectLifecycleSnapshot",
]

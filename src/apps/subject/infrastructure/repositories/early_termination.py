from dataclasses import dataclass

from django.db.models import Q

from apps.core.choices.study import (
    EventDefinitionCategoryChoices,
    EventInstanceStatusChoices,
)
from apps.study.models import EventTransitionRule
from apps.subject.models import SubjectEventInstance


@dataclass(frozen=True)
class EarlyTerminationTransitionContext:
    source_event_instance_id: int
    target_event_definition_id: int


class DjangoSubjectEarlyTerminationRepository:
    EARLY_TERMINATION_FACT = "early_termination.requested"
    EARLY_TERMINATION_EVENT_CODE = "ET"
    EOS_REACHED_STATUSES = (
        EventInstanceStatusChoices.OPEN,
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

    def get_early_termination_transition_context(
        self,
        *,
        study_id: int,
        subject_id: int,
    ) -> EarlyTerminationTransitionContext | None:
        transition_rules = (
            EventTransitionRule.objects.select_related(
                "condition_definition",
                "to_event_definition",
            )
            .filter(
                study_id=study_id,
                deleted=False,
                is_enabled=True,
                auto_open=True,
                to_event_definition__deleted=False,
            )
            .filter(
                Q(condition_code=self.EARLY_TERMINATION_FACT)
                | Q(condition_definition__code=self.EARLY_TERMINATION_FACT)
                | Q(to_event_definition__code=self.EARLY_TERMINATION_EVENT_CODE)
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
            if source_event_instance_id is not None:
                return EarlyTerminationTransitionContext(
                    source_event_instance_id=source_event_instance_id,
                    target_event_definition_id=transition_rule.to_event_definition_id,
                )
        return None

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


__all__ = [
    "DjangoSubjectEarlyTerminationRepository",
    "EarlyTerminationTransitionContext",
]

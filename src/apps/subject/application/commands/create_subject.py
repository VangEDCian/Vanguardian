from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.study.models import EventDefinition, Study
from apps.study.models import EventTransitionRule
from apps.study.application.services.study_subject_code_generation import (
    StudySubjectCodeGenerationService,
)
from apps.study.application.use_cases import StudyEventTransitionRuleAutoOpenUseCase
from apps.subject.models import Subject, SubjectEventInstance


class StudyNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class CreateSubjectCommand:
    study_id: int
    site_id: int
    actor_user_id: int


class CreateSubjectService:
    transition_rule_auto_open_use_case_class = StudyEventTransitionRuleAutoOpenUseCase

    def execute(self, command: CreateSubjectCommand) -> Subject:
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                with transaction.atomic():
                    return self._create_once(command=command)
            except IntegrityError:
                if attempt == max_retries:
                    raise

        raise RuntimeError("Unexpected subject creation retry flow.")

    @staticmethod
    def _create_once(command: CreateSubjectCommand) -> Subject:
        study = (
            Study.objects.select_for_update()
            .filter(pk=command.study_id, deleted=False)
            .only("id", "code")
            .first()
        )
        if study is None:
            raise StudyNotFoundError(command.study_id)

        max_current_sequence = Subject.objects.filter(study_id=command.study_id).aggregate(
            max_current_sequence=Max("current_sequence"),
        )["max_current_sequence"] or 0
        next_current_sequence = max_current_sequence + 1
        generated_codes = StudySubjectCodeGenerationService().generate(
            study_code=study.code,
            current_sequence=next_current_sequence,
        )
        now = timezone.now()
        subject = Subject.objects.create(
            subject_code=generated_codes.subject_code,
            screening_code=generated_codes.screening_code,
            current_sequence=next_current_sequence,
            site_id=command.site_id,
            study_id=command.study_id,
            created_at=now,
            updated_at=now,
            created_by_id=command.actor_user_id,
            updated_by_id=command.actor_user_id,
        )
        CreateSubjectService._initialize_subject_event_instances(
            subject=subject,
            actor_user_id=command.actor_user_id,
            now=now,
        )
        return subject

    @staticmethod
    def _initialize_subject_event_instances(
        *,
        subject: Subject,
        actor_user_id: int,
        now,
    ) -> None:
        event_definitions = list(
            EventDefinition.objects.filter(
                study_id=subject.study_id,
                deleted=False,
                is_enabled=True,
            )
            .only("id", "study_version", "code", "name", "event_type", "sequence_no")
            .order_by("sequence_no", "id")
        )
        if not event_definitions:
            return

        transition_rules = list(
            EventTransitionRule.objects.filter(
                study_id=subject.study_id,
                deleted=False,
                is_enabled=True,
                to_event_definition_id__in=[event_definition.pk for event_definition in event_definitions],
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
        status_by_event_definition = (
            CreateSubjectService.transition_rule_auto_open_use_case_class()
            .resolve_initial_status_by_event_definition(
                event_definitions=event_definitions,
                transition_rules=transition_rules,
                condition_flags=CreateSubjectService._build_initial_condition_flags(subject=subject),
                existing_status_by_event_definition={},
            )
        )

        SubjectEventInstance.objects.bulk_create(
            [
                SubjectEventInstance(
                    study_id=subject.study_id,
                    subject_id=subject.pk,
                    event_definition_id=event_definition.pk,
                    study_version=event_definition.study_version,
                    repeat_index=1,
                    status=status_by_event_definition.get(event_definition.pk, "not_ready"),
                    event_code_snapshot=event_definition.code,
                    event_name_snapshot=event_definition.name,
                    event_type_snapshot=event_definition.event_type,
                    created_at=now,
                    updated_at=now,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                )
                for event_definition in event_definitions
            ]
        )

    @staticmethod
    def _build_initial_condition_flags(*, subject: Subject) -> dict[str, bool]:
        return {
            "subject_created": True,
            "subject.created": True,
            "subject_is_enrolled": False,
            "subject.is_enrolled": False,
            "subject_randomized": False,
            "subject.randomized": False,
            f"study.{subject.study_id}.subject_created": True,
        }

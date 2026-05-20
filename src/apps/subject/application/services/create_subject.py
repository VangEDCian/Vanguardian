from datetime import datetime, timedelta

from django.db import IntegrityError, transaction

from apps.study.application.services.study_subject_code_generation import (
    StudySubjectCodeGenerationService,
)
from apps.study.application.use_cases import StudyEventTransitionRuleAutoOpenUseCase
from apps.subject.application.commands.create_subject import (
    CreateSubjectCommand,
    StudyNotFoundError,
)
from apps.subject.application.services.workflow_action import SubjectWorkflowActionService
from apps.subject.domain import SubjectEventInstance
from apps.subject.infrastructure.repositories import DjangoSubjectCommandRepository


class CreateSubjectService:
    repository_class = DjangoSubjectCommandRepository
    transition_rule_auto_open_use_case_class = StudyEventTransitionRuleAutoOpenUseCase
    workflow_action_service_class = SubjectWorkflowActionService

    def __init__(
        self,
        repository=None,
        code_generation_service=None,
        transition_rule_auto_open_use_case=None,
        workflow_action_service=None,
    ):
        self.repository = repository or self.repository_class()
        self.code_generation_service = code_generation_service or StudySubjectCodeGenerationService()
        self.transition_rule_auto_open_use_case = (
            transition_rule_auto_open_use_case or self.transition_rule_auto_open_use_case_class()
        )
        self.workflow_action_service = workflow_action_service or self.workflow_action_service_class()

    def execute(self, command: CreateSubjectCommand):
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                with transaction.atomic():
                    return self._create_once(command=command)
            except IntegrityError:
                if attempt == max_retries:
                    raise

        raise RuntimeError("Unexpected subject creation retry flow.")

    def _create_once(self, command: CreateSubjectCommand):
        study = self.repository.get_study_for_update(study_id=command.study_id)
        if study is None:
            raise StudyNotFoundError(command.study_id)

        next_current_sequence = self.repository.get_next_subject_sequence(study_id=command.study_id)
        generated_codes = self.code_generation_service.generate(
            study_code=study.code,
            current_sequence=next_current_sequence,
        )
        now = self.repository.now()
        subject = self.repository.create_subject(
            subject_code=generated_codes.subject_code,
            screening_code=generated_codes.screening_code,
            current_sequence=next_current_sequence,
            site_id=command.site_id,
            study_id=command.study_id,
            actor_user_id=command.actor_user_id,
            now=now,
        )
        self._initialize_subject_event_instances(
            subject=subject,
            actor_user_id=command.actor_user_id,
            now=now,
        )
        return subject

    def _initialize_subject_event_instances(
        self,
        *,
        subject,
        actor_user_id: int,
        now,
    ) -> None:
        event_definitions = self.repository.list_enabled_event_definitions(study_id=subject.study_id)
        if not event_definitions:
            return

        transition_rules = self.repository.list_enabled_transition_rules(
            study_id=subject.study_id,
            event_definition_ids=[event_definition.pk for event_definition in event_definitions],
        )
        planned_date_by_event_definition = self._build_planned_date_by_event_definition(
            transition_rules=transition_rules,
            anchor_datetime=now,
        )
        status_by_event_definition = (
            self.transition_rule_auto_open_use_case.resolve_initial_status_by_event_definition(
                event_definitions=event_definitions,
                transition_rules=transition_rules,
                condition_flags=self._build_initial_condition_flags(subject=subject),
                existing_status_by_event_definition={},
            )
        )

        self.repository.bulk_create_event_instances(
            [
                self._build_initial_event_instance(
                    subject=subject,
                    event_definition=event_definition,
                    status=status_by_event_definition.get(event_definition.pk, SubjectEventInstance.NOT_READY),
                    planned_date=planned_date_by_event_definition.get(event_definition.pk),
                    actor_user_id=actor_user_id,
                    now=now,
                )
                for event_definition in event_definitions
            ]
        )
        for event_instance_id in self.repository.list_open_event_instance_ids_for_subject(subject_id=subject.pk):
            self.workflow_action_service.execute_for_open_event(
                event_instance_id=event_instance_id,
                actor_user_id=actor_user_id,
            )

    def _build_initial_event_instance(
        self,
        *,
        subject,
        event_definition,
        status: str,
        planned_date,
        actor_user_id: int,
        now,
    ):
        if status == SubjectEventInstance.OPEN:
            planned_date = planned_date or now
            opened_at = now
            opened_by_id = actor_user_id
        else:
            opened_at = None
            opened_by_id = None

        return self.repository.build_event_instance(
            study_id=subject.study_id,
            subject_id=subject.pk,
            event_definition_id=event_definition.pk,
            study_version=event_definition.study_version,
            repeat_index=1,
            planned_date=planned_date,
            status=status,
            opened_at=opened_at,
            opened_by_id=opened_by_id,
            event_code_snapshot=event_definition.code,
            event_name_snapshot=event_definition.name,
            event_type_snapshot=event_definition.event_type,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    @staticmethod
    def _build_planned_date_by_event_definition(*, transition_rules, anchor_datetime) -> dict[int, datetime]:
        planned_date_by_event_definition = {}
        for transition_rule in transition_rules:
            if transition_rule.offset_days is None:
                continue
            planned_date_by_event_definition.setdefault(
                transition_rule.to_event_definition_id,
                anchor_datetime + timedelta(days=transition_rule.offset_days),
            )
        return planned_date_by_event_definition

    @staticmethod
    def _build_initial_condition_flags(*, subject) -> dict[str, bool]:
        return {
            "subject_created": True,
            "subject.created": True,
            "subject_is_enrolled": False,
            "subject.is_enrolled": False,
            "subject_randomized": False,
            "subject.randomized": False,
            f"study.{subject.study_id}.subject_created": True,
        }


__all__ = ["CreateSubjectService"]

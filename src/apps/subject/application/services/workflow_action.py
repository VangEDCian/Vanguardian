from dataclasses import dataclass

from django.db import transaction

from apps.study.public import randomize_subject
from apps.subject.infrastructure.repositories.workflow_action import (
    DjangoSubjectWorkflowActionRepository,
)

_EVENT_STATUS_OPEN = "open"
_EVENT_TYPE_OPERATIONAL = "operational"
_EXECUTION_MODE_WORKFLOW_ACTION = "workflow_action"
_EVENT_CATEGORY_RANDOMIZATION = "randomization"
_EVENT_CODE_ELIGIBILITY_ASSESSMENT = "eligibility_assessment"
_EVENT_CODE_ENROLLMENT = "enrollment"
_ASSESSMENT_TYPE_SCREENING = "SCREENING"
_ELIGIBILITY_ASSESSMENT_RULE_CODE = "ELIGIBILITY_RULE_V1"


@dataclass(frozen=True)
class SubjectWorkflowActionResult:
    event_instance_id: int
    executed: bool = False
    action: str = ""
    reason: str = ""


def _default_source_page_state_resolver(*, event_instance_id: int) -> int | None:
    from apps.datacapture.public import get_latest_submitted_or_stable_page_state_id_for_event_instance

    return get_latest_submitted_or_stable_page_state_id_for_event_instance(
        event_instance_id=event_instance_id
    )


def _default_eligibility_assessment_finalizer(command):
    from apps.study.public import finalize_subject_eligibility_assessment

    return finalize_subject_eligibility_assessment(command)


def _default_subject_enroller(command):
    from apps.study.public import enroll_subject_after_eligibility_gate

    return enroll_subject_after_eligibility_gate(command)


def _default_source_event_certification_checker(*, event_instance_id: int) -> bool:
    from apps.datacapture.public import has_current_event_certification_attestation

    return has_current_event_certification_attestation(event_instance_id=event_instance_id)


class SubjectWorkflowActionService:
    repository_class = DjangoSubjectWorkflowActionRepository

    def __init__(
        self,
        repository=None,
        randomization_slot_assigner=None,
        source_page_state_resolver=None,
        eligibility_assessment_finalizer=None,
        subject_enroller=None,
        source_event_certification_checker=None,
        transition_service=None,
    ):
        self.repository = repository or self.repository_class()
        self.randomize_subject = randomization_slot_assigner or randomize_subject
        self.source_page_state_resolver = source_page_state_resolver or _default_source_page_state_resolver
        self.eligibility_assessment_finalizer = (
            eligibility_assessment_finalizer or _default_eligibility_assessment_finalizer
        )
        self.subject_enroller = subject_enroller or _default_subject_enroller
        self.source_event_certification_checker = (
            source_event_certification_checker or _default_source_event_certification_checker
        )
        self.transition_service = transition_service

    def can_trigger_event_instance(
        self,
        *,
        study_id: int,
        subject_id: int,
        event_instance_id: int,
    ) -> bool:
        return self.repository.is_open_workflow_action_event(
            study_id=study_id,
            subject_id=subject_id,
            event_instance_id=event_instance_id,
        )

    def map_triggerable_event_instance_id_by_subject_id(
        self,
        *,
        study_id: int,
        subject_ids,
    ) -> dict[int, int]:
        return self.repository.map_open_workflow_action_event_id_by_subject_id(
            study_id=study_id,
            subject_ids=subject_ids,
        )

    def execute_for_open_event(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
        source_event_instance_id: int | None = None,
    ) -> SubjectWorkflowActionResult:
        with transaction.atomic():
            event = self.repository.get_event_workflow_context_for_update(event_instance_id=event_instance_id)
            if event is None:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_found")
            if (event.status or "").strip().lower() != _EVENT_STATUS_OPEN:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_open")
            if (event.event_type or "").strip().lower() != _EVENT_TYPE_OPERATIONAL:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_operational")
            if (event.execution_mode or "").strip().lower() != _EXECUTION_MODE_WORKFLOW_ACTION:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="event_not_workflow_action")
            event_code = (event.event_code or "").strip().lower()
            if event_code == _EVENT_CODE_ELIGIBILITY_ASSESSMENT:
                return self._execute_eligibility_assessment_workflow(
                    event=event,
                    actor_user_id=actor_user_id,
                    source_event_instance_id=source_event_instance_id,
                )
            if event_code == _EVENT_CODE_ENROLLMENT:
                return self._execute_enrollment_workflow(
                    event=event,
                    actor_user_id=actor_user_id,
                )
            if (event.event_category or "").strip().lower() != _EVENT_CATEGORY_RANDOMIZATION:
                return SubjectWorkflowActionResult(event_instance_id=event_instance_id, reason="unsupported_workflow_action")
            assignment = self.randomize_subject(
                subject_id=event.subject_id,
                event_instance_id=event_instance_id,
                event_definition_id=event.event_definition_id,
                actor_id=actor_user_id,
                source="workflow_action",
            )
            if assignment is None:
                return SubjectWorkflowActionResult(
                    event_instance_id=event_instance_id,
                    action=_EVENT_CATEGORY_RANDOMIZATION,
                    reason="no_available_randomization_slot",
                )

            self._complete_randomization_workflow_event(
                event=event,
                assignment=assignment,
                actor_user_id=actor_user_id,
                reason="randomization_assigned" if getattr(assignment, "randomization_event_id", None) else "subject_already_randomized",
            )
            return SubjectWorkflowActionResult(
                event_instance_id=event_instance_id,
                executed=True,
                action=_EVENT_CATEGORY_RANDOMIZATION,
                reason="randomization_assigned" if getattr(assignment, "randomization_event_id", None) else "subject_already_randomized",
            )

    def _complete_randomization_workflow_event(
        self,
        *,
        event,
        assignment,
        actor_user_id: int | None,
        reason: str,
    ) -> bool:
        completed = self.repository.complete_workflow_event_instance(
            event_instance_id=event.event_instance_id,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
            reason=reason,
        )
        if completed:
            self._trigger_downstream_transition(
                event_instance_id=event.event_instance_id,
                facts=self._randomization_facts(assignment),
                actor_user_id=actor_user_id,
            )
        return completed

    def _execute_eligibility_assessment_workflow(
        self,
        *,
        event,
        actor_user_id: int | None,
        source_event_instance_id: int | None,
    ) -> SubjectWorkflowActionResult:
        source_event_instance_id = source_event_instance_id or (
            self.repository.resolve_source_event_instance_id_for_workflow_event(
                event_instance_id=event.event_instance_id,
            )
        )
        if source_event_instance_id is None:
            return SubjectWorkflowActionResult(
                event_instance_id=event.event_instance_id,
                action=_EVENT_CODE_ELIGIBILITY_ASSESSMENT,
                reason="eligibility_source_event_not_found",
            )
        if not self.source_event_certification_checker(event_instance_id=source_event_instance_id):
            return SubjectWorkflowActionResult(
                event_instance_id=event.event_instance_id,
                action=_EVENT_CODE_ELIGIBILITY_ASSESSMENT,
                reason="eligibility_source_event_certification_required",
            )

        source_page_state_id = self.source_page_state_resolver(event_instance_id=source_event_instance_id)
        if source_page_state_id is None:
            return SubjectWorkflowActionResult(
                event_instance_id=event.event_instance_id,
                action=_EVENT_CODE_ELIGIBILITY_ASSESSMENT,
                reason="eligibility_source_page_state_not_found",
            )

        from apps.study.public import FinalizeEligibilityAssessmentCommand

        assessment = self.eligibility_assessment_finalizer(
            FinalizeEligibilityAssessmentCommand(
                study_id=event.study_id,
                site_id=event.site_id,
                subject_id=event.subject_id,
                assessment_type=_ASSESSMENT_TYPE_SCREENING,
                source_context="datacapture",
                source_object_type="PAGE_STATE",
                source_object_id=source_page_state_id,
                study_version=event.study_version,
                actor_id=actor_user_id,
                event_instance_id=event.event_instance_id,
                source_page_state_id=source_page_state_id,
                rule_code=_ELIGIBILITY_ASSESSMENT_RULE_CODE,
            )
        )
        now = self.repository.now()
        completed = self.repository.complete_workflow_event_instance(
            event_instance_id=event.event_instance_id,
            actor_user_id=actor_user_id,
            now=now,
            reason="eligibility_assessment_finalized",
        )
        if completed:
            self._trigger_downstream_transition(
                event_instance_id=event.event_instance_id,
                facts=self._eligibility_latest_facts(assessment),
                actor_user_id=actor_user_id,
            )
        return SubjectWorkflowActionResult(
            event_instance_id=event.event_instance_id,
            executed=True,
            action=_EVENT_CODE_ELIGIBILITY_ASSESSMENT,
            reason="eligibility_assessment_finalized",
        )

    def _execute_enrollment_workflow(
        self,
        *,
        event,
        actor_user_id: int | None,
    ) -> SubjectWorkflowActionResult:
        from apps.study.public import EligibilityEnrollmentGateError, EnrollSubjectCommand

        try:
            self.subject_enroller(
                EnrollSubjectCommand(
                    study_id=event.study_id,
                    site_id=event.site_id,
                    subject_id=event.subject_id,
                    actor_id=actor_user_id,
                    assessment_type=_ASSESSMENT_TYPE_SCREENING,
                )
            )
        except EligibilityEnrollmentGateError:
            return SubjectWorkflowActionResult(
                event_instance_id=event.event_instance_id,
                action=_EVENT_CODE_ENROLLMENT,
                reason="enrollment_gate_failed",
            )

        now = self.repository.now()
        completed = self.repository.complete_workflow_event_instance(
            event_instance_id=event.event_instance_id,
            actor_user_id=actor_user_id,
            now=now,
            reason="subject_enrolled",
        )
        if completed:
            self._trigger_downstream_transition(
                event_instance_id=event.event_instance_id,
                facts={},
                actor_user_id=actor_user_id,
            )
        return SubjectWorkflowActionResult(
            event_instance_id=event.event_instance_id,
            executed=True,
            action=_EVENT_CODE_ENROLLMENT,
            reason="subject_enrolled",
        )

    def _trigger_downstream_transition(self, *, event_instance_id: int, facts: dict, actor_user_id: int | None) -> None:
        if self.transition_service is None:
            from apps.subject.application import (
                SubjectEventTransitionService,
                TriggerSubjectEventTransitionCommand,
            )

            transition_service = SubjectEventTransitionService()
            command_class = TriggerSubjectEventTransitionCommand
        else:
            transition_service = self.transition_service
            from apps.subject.application import TriggerSubjectEventTransitionCommand

            command_class = TriggerSubjectEventTransitionCommand

        transition_service.execute(
            command_class(
                source_event_instance_id=event_instance_id,
                facts=facts,
                actor_user_id=actor_user_id,
                trigger_source="workflow_action",
            )
        )

    @staticmethod
    def _eligibility_latest_facts(assessment) -> dict:
        is_final_eligible = bool(
            getattr(assessment, "assessment_status", None) == "FINAL"
            and getattr(assessment, "result", None) == "ELIGIBLE"
            and getattr(assessment, "is_current", False)
        )
        is_final_not_eligible = bool(
            getattr(assessment, "assessment_status", None) == "FINAL"
            and getattr(assessment, "result", None) == "NOT_ELIGIBLE"
            and getattr(assessment, "is_current", False)
        )
        return {
            "eligibility.latest.result": getattr(assessment, "result", None),
            "eligibility.latest.assessment_status": getattr(assessment, "assessment_status", None),
            "eligibility.latest.is_current": getattr(assessment, "is_current", False),
            "eligible": is_final_eligible,
            "not_eligible": is_final_not_eligible,
        }

    @staticmethod
    def _randomization_facts(assignment) -> dict:
        facts = {
            "randomization.assigned": True,
            "randomization.status.randomized": True,
        }
        if assignment is not None:
            facts.update(
                {
                    "randomization.latest.slot_id": getattr(assignment, "slot_id", None),
                    "randomization.latest.scheme_id": getattr(assignment, "scheme_id", None),
                    "randomization.latest.scheme_code": getattr(assignment, "scheme_code", None),
                    "randomization.latest.arm_id": getattr(assignment, "arm_id", None),
                    "randomization.latest.arm_code": getattr(assignment, "arm_code", None),
                    "randomization.latest.sequence_no": getattr(assignment, "sequence_no", None),
                }
            )
        return facts


__all__ = [
    "SubjectWorkflowActionResult",
    "SubjectWorkflowActionService",
]

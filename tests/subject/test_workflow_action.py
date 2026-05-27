from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.subject.application.services.workflow_action import SubjectWorkflowActionService
from apps.subject.infrastructure.repositories.workflow_action import SubjectEventWorkflowContext


class SubjectWorkflowActionServiceTests(SimpleTestCase):
    def test_open_operational_randomization_workflow_assigns_slot_and_creates_subject_result(self):
        repository = _WorkflowRepositoryStub()
        assigner = _RandomizationSlotAssignerStub()
        transition_service = _TransitionServiceStub()

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                randomization_slot_assigner=assigner,
                transition_service=transition_service,
            ).execute_for_open_event(
                event_instance_id=30,
                actor_user_id=99,
            )

        self.assertTrue(result.executed)
        self.assertEqual(result.action, "randomization")
        self.assertEqual(
            assigner.calls,
            [
                {
                    "study_id": 1,
                    "subject_id": 20,
                    "event_instance_id": 30,
                    "actor_user_id": 99,
                }
            ],
        )
        self.assertEqual(repository.created_randomizations[0]["subject_id"], 20)
        self.assertEqual(repository.created_randomizations[0]["assignment"].sequence_no, 42)
        self.assertEqual(repository.completed_events[0]["event_instance_id"], 30)
        self.assertEqual(repository.completed_events[0]["reason"], "randomization_assigned")
        self.assertEqual(transition_service.commands[0].source_event_instance_id, 30)
        self.assertTrue(transition_service.commands[0].facts["randomization.assigned"])
        self.assertEqual(transition_service.commands[0].facts["randomization.latest.sequence_no"], 42)

    def test_non_workflow_action_event_is_ignored(self):
        repository = _WorkflowRepositoryStub(
            event=SubjectEventWorkflowContext(
                event_instance_id=30,
                study_id=1,
                subject_id=20,
                site_id=2,
                study_version="v1.0",
                status="open",
                event_definition_id=100,
                event_code="RANDOMIZATION",
                event_type="operational",
                event_category="randomization",
                execution_mode="form_entry",
            )
        )
        assigner = _RandomizationSlotAssignerStub()

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                randomization_slot_assigner=assigner,
            ).execute_for_open_event(
                event_instance_id=30,
                actor_user_id=99,
            )

        self.assertFalse(result.executed)
        self.assertEqual(result.reason, "event_not_workflow_action")
        self.assertEqual(assigner.calls, [])
        self.assertEqual(repository.created_randomizations, [])

    def test_existing_subject_randomization_is_idempotent(self):
        repository = _WorkflowRepositoryStub(has_randomization=True)
        assigner = _RandomizationSlotAssignerStub()
        transition_service = _TransitionServiceStub()

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                randomization_slot_assigner=assigner,
                transition_service=transition_service,
            ).execute_for_open_event(
                event_instance_id=30,
                actor_user_id=99,
            )

        self.assertTrue(result.executed)
        self.assertEqual(result.reason, "subject_already_randomized")
        self.assertEqual(assigner.calls, [])
        self.assertEqual(repository.created_randomizations, [])
        self.assertEqual(repository.completed_events[0]["event_instance_id"], 30)
        self.assertEqual(repository.completed_events[0]["reason"], "subject_already_randomized")
        self.assertEqual(transition_service.commands[0].source_event_instance_id, 30)
        self.assertTrue(transition_service.commands[0].facts["randomization.assigned"])

    def test_maps_triggerable_workflow_events_by_subject_id(self):
        repository = _WorkflowRepositoryStub(triggerable_event_map={20: 60})

        result = SubjectWorkflowActionService(repository=repository).map_triggerable_event_instance_id_by_subject_id(
            study_id=1,
            subject_ids=(20, 21),
        )

        self.assertEqual(result, {20: 60})
        self.assertEqual(
            repository.triggerable_event_map_calls,
            [
                {
                    "study_id": 1,
                    "subject_ids": (20, 21),
                }
            ],
        )

    def test_eligibility_assessment_workflow_finalizes_and_triggers_downstream_transition(self):
        repository = _WorkflowRepositoryStub(
            event=SubjectEventWorkflowContext(
                event_instance_id=60,
                study_id=1,
                subject_id=20,
                site_id=2,
                study_version="v1.0",
                status="open",
                event_definition_id=29,
                event_code="ELIGIBILITY_ASSESSMENT",
                event_type="operational",
                event_category="screening",
                execution_mode="workflow_action",
            )
        )
        finalizer = _EligibilityFinalizerStub()
        transition_service = _TransitionServiceStub()

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                source_page_state_resolver=lambda *, event_instance_id: 13,
                eligibility_assessment_finalizer=finalizer,
                transition_service=transition_service,
            ).execute_for_open_event(
                event_instance_id=60,
                actor_user_id=99,
                source_event_instance_id=10,
            )

        self.assertTrue(result.executed)
        self.assertEqual(result.action, "eligibility_assessment")
        self.assertEqual(finalizer.commands[0].source_page_state_id, 13)
        self.assertEqual(finalizer.commands[0].event_instance_id, 60)
        self.assertEqual(finalizer.commands[0].rule_code, "ELIGIBILITY_RULE_V1")
        self.assertEqual(repository.completed_events[0]["reason"], "eligibility_assessment_finalized")
        self.assertEqual(transition_service.commands[0].source_event_instance_id, 60)
        self.assertEqual(transition_service.commands[0].facts["eligibility.latest.result"], "ELIGIBLE")
        self.assertTrue(transition_service.commands[0].facts["eligible"])

    def test_eligibility_assessment_manual_trigger_resolves_source_event(self):
        repository = _WorkflowRepositoryStub(
            event=SubjectEventWorkflowContext(
                event_instance_id=60,
                study_id=1,
                subject_id=20,
                site_id=2,
                study_version="v1.0",
                status="open",
                event_definition_id=29,
                event_code="ELIGIBILITY_ASSESSMENT",
                event_type="operational",
                event_category="screening",
                execution_mode="workflow_action",
            ),
            resolved_source_event_instance_id=10,
        )
        finalizer = _EligibilityFinalizerStub()
        resolved_page_state_event_ids = []

        def source_page_state_resolver(*, event_instance_id):
            resolved_page_state_event_ids.append(event_instance_id)
            return 13

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                source_page_state_resolver=source_page_state_resolver,
                eligibility_assessment_finalizer=finalizer,
                transition_service=_TransitionServiceStub(),
            ).execute_for_open_event(
                event_instance_id=60,
                actor_user_id=99,
            )

        self.assertTrue(result.executed)
        self.assertEqual(repository.resolved_source_event_calls, [60])
        self.assertEqual(resolved_page_state_event_ids, [10])
        self.assertEqual(finalizer.commands[0].source_page_state_id, 13)

    def test_enrollment_workflow_enrolls_subject_and_completes_event(self):
        repository = _WorkflowRepositoryStub(
            event=SubjectEventWorkflowContext(
                event_instance_id=70,
                study_id=1,
                subject_id=20,
                site_id=2,
                study_version="v1.0",
                status="open",
                event_definition_id=30,
                event_code="ENROLLMENT",
                event_type="operational",
                event_category="screening",
                execution_mode="workflow_action",
            )
        )
        enroller = _EnrollmentStub()
        transition_service = _TransitionServiceStub()

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                subject_enroller=enroller,
                transition_service=transition_service,
            ).execute_for_open_event(
                event_instance_id=70,
                actor_user_id=99,
            )

        self.assertTrue(result.executed)
        self.assertEqual(result.action, "enrollment")
        self.assertEqual(enroller.commands[0].subject_id, 20)
        self.assertEqual(repository.completed_events[0]["reason"], "subject_enrolled")
        self.assertEqual(transition_service.commands[0].source_event_instance_id, 70)


class _WorkflowRepositoryStub:
    def __init__(
        self,
        *,
        event=None,
        has_randomization=False,
        resolved_source_event_instance_id=None,
        triggerable_event_map=None,
    ):
        self.event = event or SubjectEventWorkflowContext(
            event_instance_id=30,
            study_id=1,
            subject_id=20,
            site_id=2,
            study_version="v1.0",
            status="open",
            event_definition_id=100,
            event_code="RANDOMIZATION",
            event_type="operational",
            event_category="randomization",
            execution_mode="workflow_action",
        )
        self._has_randomization = has_randomization
        self._resolved_source_event_instance_id = resolved_source_event_instance_id
        self._triggerable_event_map = triggerable_event_map or {}
        self.created_randomizations = []
        self.completed_events = []
        self.resolved_source_event_calls = []
        self.triggerable_event_map_calls = []

    def now(self):
        return datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)

    def get_event_workflow_context_for_update(self, *, event_instance_id):
        return self.event

    def has_subject_randomization(self, *, subject_id):
        return self._has_randomization

    def map_open_workflow_action_event_id_by_subject_id(self, **kwargs):
        self.triggerable_event_map_calls.append(kwargs)
        return self._triggerable_event_map

    def resolve_source_event_instance_id_for_workflow_event(self, *, event_instance_id):
        self.resolved_source_event_calls.append(event_instance_id)
        return self._resolved_source_event_instance_id

    def create_subject_randomization(self, **kwargs):
        self.created_randomizations.append(kwargs)

    def complete_workflow_event_instance(self, **kwargs):
        self.completed_events.append(kwargs)
        return True


class _RandomizationSlotAssignerStub:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            slot_id=5,
            scheme_id=10,
            scheme_code="RAND",
            arm_id=11,
            arm_code="A",
            arm_name="Arm A",
            sequence_no=42,
        )


class _EligibilityFinalizerStub:
    def __init__(self):
        self.commands = []

    def __call__(self, command):
        self.commands.append(command)
        return SimpleNamespace(
            assessment_id=7,
            result="ELIGIBLE",
            assessment_status="FINAL",
            is_current=True,
        )


class _EnrollmentStub:
    def __init__(self):
        self.commands = []

    def __call__(self, command):
        self.commands.append(command)
        return SimpleNamespace(
            assessment_id=7,
            result="ELIGIBLE",
            assessment_status="FINAL",
            is_current=True,
        )


class _TransitionServiceStub:
    def __init__(self):
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        return SimpleNamespace()

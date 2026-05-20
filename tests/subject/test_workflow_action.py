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

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                randomization_slot_assigner=assigner,
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

    def test_non_workflow_action_event_is_ignored(self):
        repository = _WorkflowRepositoryStub(
            event=SubjectEventWorkflowContext(
                event_instance_id=30,
                study_id=1,
                subject_id=20,
                site_id=2,
                status="open",
                event_definition_id=100,
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

        with patch("apps.subject.application.services.workflow_action.transaction.atomic", return_value=nullcontext()):
            result = SubjectWorkflowActionService(
                repository=repository,
                randomization_slot_assigner=assigner,
            ).execute_for_open_event(
                event_instance_id=30,
                actor_user_id=99,
            )

        self.assertFalse(result.executed)
        self.assertEqual(result.reason, "subject_already_randomized")
        self.assertEqual(assigner.calls, [])


class _WorkflowRepositoryStub:
    def __init__(self, *, event=None, has_randomization=False):
        self.event = event or SubjectEventWorkflowContext(
            event_instance_id=30,
            study_id=1,
            subject_id=20,
            site_id=2,
            status="open",
            event_definition_id=100,
            event_type="operational",
            event_category="randomization",
            execution_mode="workflow_action",
        )
        self._has_randomization = has_randomization
        self.created_randomizations = []

    def now(self):
        return datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)

    def get_event_workflow_context_for_update(self, *, event_instance_id):
        return self.event

    def has_subject_randomization(self, *, subject_id):
        return self._has_randomization

    def create_subject_randomization(self, **kwargs):
        self.created_randomizations.append(kwargs)


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

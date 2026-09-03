from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.application.services.due_period_transition import (
    SubjectDuePeriodTransitionService,
)


class SubjectDuePeriodTransitionServiceTests(SimpleTestCase):
    def test_due_washout_uses_workflow_event_and_falls_back_without_one(self):
        period_repository = _PeriodRepositoryStub(subject_ids=[20, 21])
        workflow_repository = _WorkflowRepositoryStub(event_ids={20: 80})
        workflow_action_service = _WorkflowActionServiceStub(executed=True)
        period_lifecycle_service = _PeriodLifecycleServiceStub(has_changes=True)

        result = SubjectDuePeriodTransitionService(
            period_repository=period_repository,
            workflow_repository=workflow_repository,
            workflow_action_service=workflow_action_service,
            period_lifecycle_service=period_lifecycle_service,
        ).process_due_transitions(
            actor_user_id=99,
            limit=10,
        )

        self.assertEqual(result.due_subject_count, 2)
        self.assertEqual(result.advanced_subject_count, 2)
        self.assertEqual(result.workflow_event_count, 1)
        self.assertEqual(
            workflow_action_service.calls,
            [
                {
                    "event_instance_id": 80,
                    "actor_user_id": 99,
                    "automatic": True,
                }
            ],
        )
        self.assertEqual(
            period_lifecycle_service.calls,
            [
                {
                    "subject_id": 21,
                    "actor_user_id": 99,
                    "trigger_source": "period_transition_due",
                }
            ],
        )

    def test_failed_workflow_action_does_not_bypass_event_audit(self):
        period_lifecycle_service = _PeriodLifecycleServiceStub(has_changes=True)

        result = SubjectDuePeriodTransitionService(
            period_repository=_PeriodRepositoryStub(subject_ids=[20]),
            workflow_repository=_WorkflowRepositoryStub(event_ids={20: 80}),
            workflow_action_service=_WorkflowActionServiceStub(executed=False),
            period_lifecycle_service=period_lifecycle_service,
        ).process_due_transitions()

        self.assertEqual(result.advanced_subject_count, 0)
        self.assertEqual(result.workflow_event_count, 0)
        self.assertEqual(period_lifecycle_service.calls, [])


class _PeriodRepositoryStub:
    def __init__(self, *, subject_ids):
        self.subject_ids = subject_ids
        self.current_time = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)

    def now(self):
        return self.current_time

    def list_due_washout_subject_ids(self, *, as_of, limit):
        return self.subject_ids[:limit]


class _WorkflowRepositoryStub:
    def __init__(self, *, event_ids):
        self.event_ids = event_ids

    def map_open_washout_event_id_by_subject_id(self, *, subject_ids):
        return {
            subject_id: self.event_ids[subject_id]
            for subject_id in subject_ids
            if subject_id in self.event_ids
        }


class _WorkflowActionServiceStub:
    def __init__(self, *, executed):
        self.executed = executed
        self.calls = []

    def execute_for_open_event(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(executed=self.executed)


class _PeriodLifecycleServiceStub:
    def __init__(self, *, has_changes):
        self.has_changes = has_changes
        self.calls = []

    def advance_after_washout(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(has_changes=self.has_changes)

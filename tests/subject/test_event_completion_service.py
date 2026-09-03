from django.test import SimpleTestCase

from apps.subject.application.services.event_completion import SubjectEventCompletionService


class SubjectEventCompletionServiceTests(SimpleTestCase):
    def test_complete_triggers_downstream_transition_when_status_changed(self):
        repository = _EventCompletionRepositoryStub(changed=True)
        period_lifecycle_service = _PeriodLifecycleServiceStub()
        transition_service = _TransitionServiceStub()
        early_termination_lifecycle_service = _EarlyTerminationLifecycleServiceStub()

        service = SubjectEventCompletionService(
            repository=repository,
            transition_service=transition_service,
            period_lifecycle_service=period_lifecycle_service,
            early_termination_lifecycle_service=early_termination_lifecycle_service,
        )
        changed = SubjectEventCompletionService.complete_event_instance.__wrapped__(
            service,
            event_instance_id=10,
            actor_user_id=99,
        )

        self.assertTrue(changed)
        self.assertEqual(early_termination_lifecycle_service.completed_event_ids, [10])
        self.assertEqual(period_lifecycle_service.event_ids, [10])
        self.assertEqual(transition_service.commands[0].source_event_instance_id, 10)
        self.assertEqual(transition_service.commands[0].actor_user_id, 99)
        self.assertEqual(transition_service.commands[0].trigger_source, "subject_event_status_changed")

    def test_verify_does_not_trigger_downstream_transition_when_status_unchanged(self):
        repository = _EventCompletionRepositoryStub(changed=False)
        period_lifecycle_service = _PeriodLifecycleServiceStub()
        transition_service = _TransitionServiceStub()
        early_termination_lifecycle_service = _EarlyTerminationLifecycleServiceStub()

        service = SubjectEventCompletionService(
            repository=repository,
            transition_service=transition_service,
            period_lifecycle_service=period_lifecycle_service,
            early_termination_lifecycle_service=early_termination_lifecycle_service,
        )
        changed = SubjectEventCompletionService.verify_event_instance.__wrapped__(
            service,
            event_instance_id=10,
            actor_user_id=99,
        )

        self.assertFalse(changed)
        self.assertEqual(early_termination_lifecycle_service.completed_event_ids, [])
        self.assertEqual(period_lifecycle_service.event_ids, [])
        self.assertEqual(transition_service.commands, [])

    def test_mark_in_progress_reopens_early_termination_lifecycle(self):
        repository = _EventCompletionRepositoryStub(changed=True)
        early_termination_lifecycle_service = _EarlyTerminationLifecycleServiceStub()
        service = SubjectEventCompletionService(
            repository=repository,
            transition_service=_TransitionServiceStub(),
            period_lifecycle_service=_PeriodLifecycleServiceStub(),
            early_termination_lifecycle_service=early_termination_lifecycle_service,
        )

        changed = SubjectEventCompletionService.mark_event_instance_in_progress.__wrapped__(
            service,
            event_instance_id=10,
            actor_user_id=99,
        )

        self.assertTrue(changed)
        self.assertEqual(early_termination_lifecycle_service.reopened_event_ids, [10])


class _EventCompletionRepositoryStub:
    def __init__(self, *, changed):
        self.changed = changed

    def now(self):
        return "2026-05-19T10:00:00"

    def complete_event_instance(self, **kwargs):
        return self.changed

    def verify_event_instance(self, **kwargs):
        return self.changed

    def mark_event_instance_in_progress(self, **kwargs):
        return self.changed


class _TransitionServiceStub:
    def __init__(self):
        self.commands = []

    def execute(self, command):
        self.commands.append(command)


class _PeriodLifecycleServiceStub:
    def __init__(self):
        self.event_ids = []

    def handle_event_status_changed(self, **kwargs):
        self.event_ids.append(kwargs["event_instance_id"])


class _EarlyTerminationLifecycleServiceStub:
    def __init__(self):
        self.completed_event_ids = []
        self.reopened_event_ids = []

    def complete_if_early_termination_event(self, **kwargs):
        self.completed_event_ids.append(kwargs["event_instance_id"])
        return False

    def reopen_if_early_termination_event(self, **kwargs):
        self.reopened_event_ids.append(kwargs["event_instance_id"])
        return False

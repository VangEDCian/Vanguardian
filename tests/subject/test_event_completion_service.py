from django.test import SimpleTestCase

from apps.subject.application.services.event_completion import SubjectEventCompletionService


class SubjectEventCompletionServiceTests(SimpleTestCase):
    def test_complete_triggers_downstream_transition_when_status_changed(self):
        repository = _EventCompletionRepositoryStub(changed=True)
        transition_service = _TransitionServiceStub()

        service = SubjectEventCompletionService(
            repository=repository,
            transition_service=transition_service,
        )
        changed = SubjectEventCompletionService.complete_event_instance.__wrapped__(
            service,
            event_instance_id=10,
            actor_user_id=99,
        )

        self.assertTrue(changed)
        self.assertEqual(transition_service.commands[0].source_event_instance_id, 10)
        self.assertEqual(transition_service.commands[0].actor_user_id, 99)
        self.assertEqual(transition_service.commands[0].trigger_source, "subject_event_status_changed")

    def test_verify_does_not_trigger_downstream_transition_when_status_unchanged(self):
        repository = _EventCompletionRepositoryStub(changed=False)
        transition_service = _TransitionServiceStub()

        service = SubjectEventCompletionService(
            repository=repository,
            transition_service=transition_service,
        )
        changed = SubjectEventCompletionService.verify_event_instance.__wrapped__(
            service,
            event_instance_id=10,
            actor_user_id=99,
        )

        self.assertFalse(changed)
        self.assertEqual(transition_service.commands, [])


class _EventCompletionRepositoryStub:
    def __init__(self, *, changed):
        self.changed = changed

    def now(self):
        return "2026-05-19T10:00:00"

    def complete_event_instance(self, **kwargs):
        return self.changed

    def verify_event_instance(self, **kwargs):
        return self.changed


class _TransitionServiceStub:
    def __init__(self):
        self.commands = []

    def execute(self, command):
        self.commands.append(command)

from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.application.services.early_termination import SubjectEarlyTerminationRequestService
from apps.subject.domain import SubjectEventTransitionApplied, SubjectEventTransitionResult
from apps.subject.infrastructure.repositories.early_termination import EarlyTerminationTransitionContext


class SubjectEarlyTerminationRequestServiceTests(SimpleTestCase):
    def test_requests_only_configured_early_termination_target(self):
        transition_service = _TransitionServiceStub(
            result=SubjectEventTransitionResult(
                source_event_instance_id=5,
                applied_events=(
                    SubjectEventTransitionApplied(
                        subject_id=20,
                        source_event_instance_id=5,
                        target_event_instance_id=23,
                        rule_id=27,
                        from_status="completed",
                        to_status="open",
                    ),
                ),
            )
        )
        service = SubjectEarlyTerminationRequestService(
            repository=_EarlyTerminationRepositoryStub(
                transition_context=EarlyTerminationTransitionContext(
                    source_event_instance_id=5,
                    target_event_definition_id=23,
                )
            ),
            transition_service=transition_service,
        )

        result = service.request(study_id=1, subject_id=20, actor_user_id=99)

        self.assertTrue(result.requested)
        self.assertEqual(result.opened_event_instance_ids, (23,))
        self.assertEqual(transition_service.command.source_event_instance_id, 5)
        self.assertEqual(transition_service.command.target_event_definition_id, 23)
        self.assertEqual(transition_service.command.facts, {"early_termination.requested": True})

    def test_rejects_request_after_eos_has_started(self):
        transition_service = _TransitionServiceStub(result=None)
        service = SubjectEarlyTerminationRequestService(
            repository=_EarlyTerminationRepositoryStub(
                eos_event=SimpleNamespace(id=88),
                transition_context=EarlyTerminationTransitionContext(
                    source_event_instance_id=5,
                    target_event_definition_id=23,
                ),
            ),
            transition_service=transition_service,
        )

        result = service.request(study_id=1, subject_id=20, actor_user_id=99)

        self.assertFalse(result.requested)
        self.assertEqual(result.reason, "final_visit_already_started")
        self.assertIsNone(transition_service.command)

    def test_rejects_request_without_configured_transition_source(self):
        transition_service = _TransitionServiceStub(result=None)
        service = SubjectEarlyTerminationRequestService(
            repository=_EarlyTerminationRepositoryStub(transition_context=None),
            transition_service=transition_service,
        )

        result = service.request(study_id=1, subject_id=20, actor_user_id=99)

        self.assertFalse(result.requested)
        self.assertEqual(result.reason, "early_termination_transition_not_available")
        self.assertIsNone(transition_service.command)


class _EarlyTerminationRepositoryStub:
    def __init__(self, *, transition_context, eos_event=None):
        self.transition_context = transition_context
        self.eos_event = eos_event

    def get_reached_eos_event_instance(self, *, study_id, subject_id):
        return self.eos_event

    def get_early_termination_transition_context(self, *, study_id, subject_id):
        return self.transition_context


class _TransitionServiceStub:
    def __init__(self, *, result):
        self.result = result
        self.command = None

    def execute(self, command):
        self.command = command
        return self.result

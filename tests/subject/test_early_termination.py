from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from apps.core.choices import SubjectLifecycleStatusChoices
from apps.subject.application.services.early_termination import (
    SubjectEarlyTerminationRequestService,
)
from apps.subject.domain import (
    SubjectEventTransitionApplied,
    SubjectEventTransitionResult,
)
from apps.subject.infrastructure.repositories.early_termination import (
    EarlyTerminationTransitionContext,
    SubjectLifecycleSnapshot,
)
from apps.subject.presentation.web.views.early_termination import (
    SubjectEarlyTerminationRequestView,
)


class SubjectEarlyTerminationRequestServiceTests(SimpleTestCase):
    def test_starts_lifecycle_and_closes_other_visits(self):
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
        repository = _EarlyTerminationRepositoryStub(
            transition_context=EarlyTerminationTransitionContext(
                source_event_instance_id=5,
                target_event_definition_id=123,
            )
        )
        service = SubjectEarlyTerminationRequestService(
            repository=repository,
            transition_service=transition_service,
        )

        result = SubjectEarlyTerminationRequestService.request.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            effective_at=repository.current_time,
            reason_code="subject_withdrawal",
            reason_text="Subject withdrew consent.",
        )

        self.assertTrue(result.requested)
        self.assertEqual(result.opened_event_instance_ids, (23,))
        self.assertEqual(result.skipped_event_count, 4)
        self.assertEqual(result.cancelled_event_count, 2)
        self.assertEqual(result.cancelled_period_count, 1)
        self.assertEqual(transition_service.command.source_event_instance_id, 5)
        self.assertEqual(transition_service.command.target_event_definition_id, 123)
        self.assertEqual(
            transition_service.command.facts,
            {"early_termination.requested": True},
        )
        self.assertEqual(repository.started_target_ids, [23])

    def test_adopts_an_already_open_early_termination_visit(self):
        transition_service = _TransitionServiceStub(result=None)
        repository = _EarlyTerminationRepositoryStub(
            transition_context=EarlyTerminationTransitionContext(
                source_event_instance_id=5,
                target_event_definition_id=123,
                target_event_instance_id=23,
                target_event_status="open",
            )
        )
        service = SubjectEarlyTerminationRequestService(
            repository=repository,
            transition_service=transition_service,
        )

        result = SubjectEarlyTerminationRequestService.request.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            effective_at=repository.current_time,
            reason_code="other",
            reason_text="Legacy target was already open.",
        )

        self.assertTrue(result.requested)
        self.assertIsNone(transition_service.command)
        self.assertEqual(result.opened_event_instance_ids, (23,))

    def test_rejects_request_after_regular_eos_has_started(self):
        transition_service = _TransitionServiceStub(result=None)
        repository = _EarlyTerminationRepositoryStub(
            eos_event=SimpleNamespace(id=88),
            transition_context=EarlyTerminationTransitionContext(
                source_event_instance_id=5,
                target_event_definition_id=23,
            ),
        )
        service = SubjectEarlyTerminationRequestService(
            repository=repository,
            transition_service=transition_service,
        )

        result = SubjectEarlyTerminationRequestService.request.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            effective_at=repository.current_time,
            reason_code="other",
            reason_text="Not applicable.",
        )

        self.assertFalse(result.requested)
        self.assertEqual(result.reason, "final_visit_already_started")
        self.assertIsNone(transition_service.command)

    def test_repeated_request_is_an_idempotent_noop(self):
        repository = _EarlyTerminationRepositoryStub(
            transition_context=None,
            lifecycle_status=(
                SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
            ),
        )
        transition_service = _TransitionServiceStub(result=None)
        service = SubjectEarlyTerminationRequestService(
            repository=repository,
            transition_service=transition_service,
        )

        result = SubjectEarlyTerminationRequestService.request.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            effective_at=repository.current_time,
            reason_code="other",
            reason_text="Repeated request.",
        )

        self.assertFalse(result.requested)
        self.assertEqual(result.reason, "early_termination_already_in_progress")
        self.assertIsNone(transition_service.command)
        self.assertEqual(repository.started_target_ids, [])

    def test_rejects_request_without_reason(self):
        repository = _EarlyTerminationRepositoryStub(transition_context=None)
        service = SubjectEarlyTerminationRequestService(
            repository=repository,
            transition_service=_TransitionServiceStub(result=None),
        )

        result = SubjectEarlyTerminationRequestService.request.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
        )

        self.assertFalse(result.requested)
        self.assertEqual(result.reason, "termination_reason_required")

    def test_rejects_subject_that_has_not_enrolled(self):
        repository = _EarlyTerminationRepositoryStub(
            transition_context=EarlyTerminationTransitionContext(
                source_event_instance_id=5,
                target_event_definition_id=123,
            ),
            is_enrolled=False,
        )
        transition_service = _TransitionServiceStub(result=None)
        service = SubjectEarlyTerminationRequestService(
            repository=repository,
            transition_service=transition_service,
        )

        result = SubjectEarlyTerminationRequestService.request.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            effective_at=repository.current_time,
            reason_code="subject_withdrawal",
            reason_text="Withdrew during screening.",
        )

        self.assertFalse(result.requested)
        self.assertEqual(result.reason, "subject_not_enrolled")
        self.assertIsNone(transition_service.command)
        self.assertEqual(repository.started_target_ids, [])


class SubjectEarlyTerminationRequestViewTests(SimpleTestCase):
    def test_uses_dedicated_permission_and_validated_termination_details(self):
        self.assertEqual(
            SubjectEarlyTerminationRequestView.permission_required,
            "SUBJECT.EARLY_TERMINATE",
        )
        next_url = reverse("subject:subject_list", kwargs={"study_id": 1})
        request = RequestFactory().post(
            "/early-termination/",
            data={
                "next": next_url,
                "reason_code": "subject_withdrawal",
                "effective_at": "2026-07-30T09:00",
                "reason_text": "Subject withdrew consent.",
            },
        )
        request.user = SimpleNamespace(pk=99)
        view = SubjectEarlyTerminationRequestView()
        view.service_class = _SuccessfulRequestService
        _SuccessfulRequestService.calls = []

        with patch(
            "apps.subject.presentation.web.views.early_termination.messages"
        ) as messages:
            response = view.post(request, study_id=1, subject_id=20)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        self.assertEqual(len(_SuccessfulRequestService.calls), 1)
        self.assertEqual(
            _SuccessfulRequestService.calls[0]["reason_code"],
            "subject_withdrawal",
        )
        self.assertEqual(
            _SuccessfulRequestService.calls[0]["reason_text"],
            "Subject withdrew consent.",
        )
        messages.success.assert_called_once()


class _EarlyTerminationRepositoryStub:
    def __init__(
        self,
        *,
        transition_context,
        eos_event=None,
        lifecycle_status=SubjectLifecycleStatusChoices.ACTIVE,
        is_enrolled=True,
    ):
        self.transition_context = transition_context
        self.eos_event = eos_event
        self.lifecycle_status = lifecycle_status
        self.is_enrolled = is_enrolled
        self.current_time = datetime(2026, 7, 30, 9, 0, tzinfo=timezone.utc)
        self.started_target_ids = []

    def now(self):
        return self.current_time

    def get_subject_for_update(self, *, study_id, subject_id):
        return SubjectLifecycleSnapshot(
            subject_id=subject_id,
            lifecycle_status=self.lifecycle_status,
            is_enrolled=self.is_enrolled,
        )

    def get_reached_regular_eos_event_instance(self, *, study_id, subject_id):
        return self.eos_event

    def get_early_termination_transition_context(self, *, study_id, subject_id):
        return self.transition_context

    def start_early_termination(self, *, subject_id, **kwargs):
        self.started_target_ids.append(
            kwargs.get("early_termination_event_instance_id", 23)
        )
        return True

    def close_other_event_instances(
        self,
        *,
        early_termination_event_instance_id,
        **kwargs,
    ):
        self.started_target_ids[-1] = early_termination_event_instance_id
        return 4, 2

    def cancel_open_subject_periods(self, **kwargs):
        return 1

    def complete_subject_if_early_termination_event(self, **kwargs):
        return False


class _TransitionServiceStub:
    def __init__(self, *, result):
        self.result = result
        self.command = None

    def execute(self, command):
        self.command = command
        return self.result


class _SuccessfulRequestService:
    calls = []

    def request(self, **kwargs):
        type(self).calls.append(kwargs)
        return SimpleNamespace(
            requested=True,
            source_event_instance_id=5,
            opened_event_instance_ids=(23,),
            reason="early_termination_started",
        )

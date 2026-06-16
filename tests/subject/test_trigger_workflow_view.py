from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from apps.subject.application.services.workflow_action import SubjectWorkflowActionResult
from apps.subject.presentation.web.views.trigger_workflow import SubjectTriggerWorkflowView


class SubjectTriggerWorkflowViewTests(SimpleTestCase):
    def test_post_triggers_open_workflow_action_and_redirects_back(self):
        next_url = reverse("subject:subject_detail", kwargs={"study_id": 1, "subject_id": 20})
        request = RequestFactory().post("/trigger-workflow/", data={"next": next_url})
        request.user = SimpleNamespace(pk=99)
        view = SubjectTriggerWorkflowView()
        view.service_class = _TriggeredWorkflowService
        _TriggeredWorkflowService.calls = []
        _TriggeredWorkflowService.can_trigger = True

        with patch("apps.subject.presentation.web.views.trigger_workflow.messages") as messages:
            response = view.post(request, study_id=1, subject_id=20, event_instance_id=60)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        self.assertEqual(
            _TriggeredWorkflowService.calls,
            [
                {
                    "event_instance_id": 60,
                    "actor_user_id": 99,
                }
            ],
        )
        messages.success.assert_called_once()

    def test_post_rejects_non_workflow_event_before_service_call(self):
        request = RequestFactory().post("/trigger-workflow/")
        request.user = SimpleNamespace(pk=99)
        view = SubjectTriggerWorkflowView()
        view.service_class = _TriggeredWorkflowService
        _TriggeredWorkflowService.calls = []
        _TriggeredWorkflowService.can_trigger = False

        with patch("apps.subject.presentation.web.views.trigger_workflow.messages") as messages:
            response = view.post(request, study_id=1, subject_id=20, event_instance_id=60)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("subject:subject_detail", kwargs={"study_id": 1, "subject_id": 20}),
        )
        self.assertEqual(_TriggeredWorkflowService.calls, [])
        messages.warning.assert_called_once()


class _TriggeredWorkflowService:
    calls = []
    can_trigger = True

    def can_trigger_event_instance(self, **kwargs):
        return self.can_trigger

    def execute_for_open_event(self, **kwargs):
        type(self).calls.append(kwargs)
        return SubjectWorkflowActionResult(
            event_instance_id=kwargs["event_instance_id"],
            executed=True,
            action="eligibility_assessment",
            reason="eligibility_assessment_finalized",
        )

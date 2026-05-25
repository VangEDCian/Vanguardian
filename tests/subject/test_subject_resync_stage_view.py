from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from apps.subject.presentation.web.views.resync_stage import SubjectResyncStageView


class SubjectResyncStageViewTests(SimpleTestCase):
    def test_post_resyncs_subject_stage_and_redirects_back(self):
        next_url = reverse("subject:subject_list", kwargs={"study_id": 1})
        request = RequestFactory().post("/resync-stage/", data={"next": next_url})
        request.user = SimpleNamespace(pk=99)
        view = SubjectResyncStageView()
        view.service_class = _ChangedResyncService
        _ChangedResyncService.calls = []

        with patch("apps.subject.presentation.web.views.resync_stage.messages") as messages:
            response = view.post(request, study_id=1, subject_id=20)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        self.assertEqual(
            _ChangedResyncService.calls,
            [
                {
                    "study_id": 1,
                    "subject_id": 20,
                    "actor_user_id": 99,
                    "trigger_source": "subject_list_resync_stage",
                }
            ],
        )
        messages.success.assert_called_once()

    def test_post_warns_when_active_stage_definition_is_missing(self):
        request = RequestFactory().post("/resync-stage/")
        request.user = SimpleNamespace(pk=99)
        view = SubjectResyncStageView()
        view.service_class = _NoActiveVersionResyncService

        with patch("apps.subject.presentation.web.views.resync_stage.messages") as messages:
            response = view.post(request, study_id=1, subject_id=20)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("subject:subject_list", kwargs={"study_id": 1}))
        messages.warning.assert_called_once()


class SubjectListActionsCellTemplateTests(SimpleTestCase):
    def test_actions_cell_renders_resync_stage_post_action_when_permitted(self):
        rendered = render_to_string(
            "subject/includes/subject_list_actions_cell.html",
            {
                "csrf_token": "test-token",
                "perms": SimpleNamespace(subject=SimpleNamespace(update_subject=True)),
                "record": SimpleNamespace(pk=20, study_id=1),
                "request": SimpleNamespace(get_full_path="/studies/1/subjects/?page=2"),
                "table": SimpleNamespace(verify_eligible_subject_ids=frozenset()),
            },
        )

        self.assertIn("Resync Stage", rendered)
        self.assertIn(reverse("subject:subject_resync_stage", kwargs={"study_id": 1, "subject_id": 20}), rendered)
        self.assertIn('method="post"', rendered)


class _ChangedResyncService:
    calls = []

    def resync_subject_active_study_version(self, **kwargs):
        type(self).calls.append(kwargs)
        return SimpleNamespace(
            study_version="v2.0",
            subject_count=1,
            event_definition_count=2,
            created_count=2,
            updated_count=1,
            skipped_terminal_count=0,
            reason="completed",
            has_changes=True,
        )


class _NoActiveVersionResyncService:
    def resync_subject_active_study_version(self, **kwargs):
        return SimpleNamespace(
            study_version="",
            subject_count=0,
            event_definition_count=0,
            created_count=0,
            updated_count=0,
            skipped_terminal_count=0,
            reason="active_study_version_not_found",
            has_changes=False,
        )

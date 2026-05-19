import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from apps.subject.presentation.web.views.verification_verify_checked import (
    SubjectFormVerificationOpenQueryView,
)


class SubjectFormVerificationOpenQueryViewTests(SimpleTestCase):
    def test_verification_api_urls_use_api_prefix(self):
        kwargs = {
            "study_id": 1,
            "subject_id": 2,
            "visit_id": 3,
            "crf_template_id": 4,
        }

        self.assertEqual(
            reverse("subject:subject_form_verification_verify_checked", kwargs=kwargs),
            "/api/studies/1/subjects/2/events/3/forms/4/verification/verify-checked/",
        )
        self.assertEqual(
            reverse("subject:subject_form_verification_reopen", kwargs=kwargs),
            "/api/studies/1/subjects/2/events/3/forms/4/verification/reopen/",
        )
        self.assertEqual(
            reverse("subject:subject_form_verification_query_thread", kwargs=kwargs),
            "/api/studies/1/subjects/2/events/3/forms/4/verification/query-thread/",
        )
        self.assertEqual(
            reverse("subject:subject_form_verification_open_query", kwargs=kwargs),
            "/api/studies/1/subjects/2/events/3/forms/4/verification/open-query/",
        )

    def test_post_maps_request_to_open_reconcile_query_api(self):
        request = RequestFactory().post(
            "/open-query/",
            data=json.dumps(
                {
                    "field_template_id": 11,
                    "message_text": "Open this query",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)
        created_at = timezone.make_aware(datetime(2026, 5, 18, 10, 0, 0))

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_id_for_subject_visit_crf",
                return_value=23,
            ) as get_page_state_id,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
                return_value=False,
            ) as is_field_verified,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked.open_reconcile_query",
                return_value={
                    "dataquery_id": 101,
                    "field_template_id": 11,
                    "message_text": "Open this query",
                    "message_type": "comment",
                    "created_at": created_at,
                },
            ) as open_reconcile_query,
        ):
            response = SubjectFormVerificationOpenQueryView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["dataquery_id"], 101)
        self.assertEqual(payload["field_template_id"], 11)
        get_page_state_id.assert_called_once_with(
            subject_id=2,
            visit_id=3,
            crf_template_id=4,
        )
        is_field_verified.assert_called_once_with(page_state_id=23, field_template_id=11)
        open_reconcile_query.assert_called_once_with(
            page_state_id=23,
            field_template_id=11,
            message_text="Open this query",
            actor_user_id=7,
        )

    def test_post_returns_400_when_open_query_already_exists(self):
        request = RequestFactory().post(
            "/open-query/",
            data=json.dumps(
                {
                    "field_template_id": 11,
                    "message_text": "Open this query",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_id_for_subject_visit_crf",
                return_value=23,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked.open_reconcile_query",
                side_effect=ValueError("An open query already exists for this field."),
            ),
        ):
            response = SubjectFormVerificationOpenQueryView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"], ["An open query already exists for this field."])

    def test_post_returns_400_when_field_is_verified(self):
        request = RequestFactory().post(
            "/open-query/",
            data=json.dumps(
                {
                    "field_template_id": 11,
                    "message_text": "Open this query",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_id_for_subject_visit_crf",
                return_value=23,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
                return_value=True,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked.open_reconcile_query",
            ) as open_reconcile_query,
        ):
            response = SubjectFormVerificationOpenQueryView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"], ["Dữ liệu đã được verify không thể tạo Query"])
        open_reconcile_query.assert_not_called()

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from apps.subject.presentation.web.views.verification_verify_checked import (
    SubjectFormVerificationOpenQueryView,
    SubjectFormVerificationQueryThreadView,
    SubjectFormVerificationVerifyCheckedView,
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
                    "field_key": "AE_TERM__repeat_2",
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
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ) as get_page_state_status,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
                return_value=False,
            ) as is_field_verified,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "has_verified_reconcile_query_for_page_field",
                return_value=False,
            ) as has_verified_query,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
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
        get_page_state_status.assert_called_once_with(
            subject_id=2,
            visit_id=3,
            crf_template_id=4,
        )
        is_field_verified.assert_called_once_with(page_state_id=23, field_template_id=11)
        has_verified_query.assert_called_once_with(page_state_id=23, field_template_id=11)
        open_reconcile_query.assert_called_once_with(
            page_state_id=23,
            field_template_id=11,
            field_key="AE_TERM__repeat_2",
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
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "has_verified_reconcile_query_for_page_field",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
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

    def test_post_returns_400_when_page_state_is_not_submitted(self):
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
                "get_page_state_status_for_subject_visit_crf",
                return_value="in_progress",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
            ) as is_field_verified,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "has_verified_reconcile_query_for_page_field",
            ) as has_verified_query,
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
        self.assertEqual(payload["error"], ["Chỉ được tạo Query khi Page State ở trạng thái Submitted."])
        is_field_verified.assert_not_called()
        has_verified_query.assert_not_called()
        open_reconcile_query.assert_not_called()

    def test_post_returns_400_when_current_user_last_updated_submitted_entry(self):
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
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=True,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
            ) as is_field_verified,
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
        self.assertEqual(payload["error"], ["Bạn không được verify hoặc thao tác Query cho form do chính bạn cập nhật."])
        is_field_verified.assert_not_called()
        open_reconcile_query.assert_not_called()

    def test_verify_checked_returns_400_when_current_user_last_updated_submitted_entry(self):
        request = RequestFactory().post(
            "/verify-checked/",
            data=json.dumps(
                {
                    "field_template_ids": [11],
                    "reason_text": "Revert verification",
                    "review_page_entry_id": "101",
                    "review_entry_version": "1",
                    "review_page_status": "submitted",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_latest_submitted_page_entry_for_subject_visit_crf",
                return_value=SimpleNamespace(id=101, entry_version="1"),
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=True,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "merge_form_verification_checked_fields_into_page_state_final_data",
            ) as merge_checked,
        ):
            response = SubjectFormVerificationVerifyCheckedView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"], ["Bạn không được verify hoặc thao tác Query cho form do chính bạn cập nhật."])
        merge_checked.assert_not_called()

    def test_verify_checked_returns_unverified_field_template_ids(self):
        request = RequestFactory().post(
            "/verify-checked/",
            data=json.dumps(
                {
                    "field_template_ids": [11],
                    "reason_text": "Revert verification",
                    "review_page_entry_id": "101",
                    "review_entry_version": "1",
                    "review_page_status": "submitted",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ) as get_page_state_status,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_latest_submitted_page_entry_for_subject_visit_crf",
                return_value=SimpleNamespace(id=101, entry_version="1"),
            ) as get_latest_submitted,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "merge_form_verification_checked_fields_into_page_state_final_data",
                return_value=(False, "under_review", ["field_review_not_ready:12"], [12]),
            ) as merge_checked,
        ):
            response = SubjectFormVerificationVerifyCheckedView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["field_template_ids"], [11])
        self.assertEqual(payload["unverified_field_template_ids"], [12])
        self.assertEqual(payload["page_status"], "under_review")
        get_page_state_status.assert_called_once_with(subject_id=2, visit_id=3, crf_template_id=4)
        get_latest_submitted.assert_called_once_with(subject_id=2, visit_id=3, crf_template_id=4)
        merge_checked.assert_called_once_with(
            subject_id=2,
            visit_id=3,
            crf_template_id=4,
            checked_field_template_ids=[11],
            unverify_reason_text="Revert verification",
            actor_user_id=7,
        )

    def test_verify_checked_returns_400_when_review_entry_version_is_stale(self):
        request = RequestFactory().post(
            "/verify-checked/",
            data=json.dumps(
                {
                    "field_template_ids": [11],
                    "review_page_entry_id": "101",
                    "review_entry_version": "1",
                    "review_page_status": "submitted",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_latest_submitted_page_entry_for_subject_visit_crf",
                return_value=SimpleNamespace(id=102, entry_version="2"),
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "merge_form_verification_checked_fields_into_page_state_final_data",
            ) as merge_checked,
        ):
            response = SubjectFormVerificationVerifyCheckedView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"], ["Dữ liệu đã bị thao tác, vui lòng reload lại trang để tiếp tục"])
        merge_checked.assert_not_called()

    def test_verify_checked_returns_400_when_review_page_status_is_stale(self):
        request = RequestFactory().post(
            "/verify-checked/",
            data=json.dumps(
                {
                    "field_template_ids": [11],
                    "review_page_entry_id": "101",
                    "review_entry_version": "1",
                    "review_page_status": "submitted",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_status_for_subject_visit_crf",
                return_value="verified",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_latest_submitted_page_entry_for_subject_visit_crf",
            ) as get_latest_submitted,
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "merge_form_verification_checked_fields_into_page_state_final_data",
            ) as merge_checked,
        ):
            response = SubjectFormVerificationVerifyCheckedView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"], ["Dữ liệu đã bị thao tác, vui lòng reload lại trang để tiếp tục"])
        get_latest_submitted.assert_not_called()
        merge_checked.assert_not_called()

    def test_verify_checked_allows_page_status_to_move_from_submitted_to_under_review(self):
        request = RequestFactory().post(
            "/verify-checked/",
            data=json.dumps(
                {
                    "field_template_ids": [11],
                    "review_page_entry_id": "101",
                    "review_entry_version": "1",
                    "review_page_status": "submitted",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_status_for_subject_visit_crf",
                return_value="under_review",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_latest_submitted_page_entry_for_subject_visit_crf",
                return_value=SimpleNamespace(id=101, entry_version="1"),
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "merge_form_verification_checked_fields_into_page_state_final_data",
                return_value=(False, "under_review", [], []),
            ) as merge_checked,
        ):
            response = SubjectFormVerificationVerifyCheckedView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["page_status"], "under_review")
        merge_checked.assert_called_once()

    def test_verify_checked_falls_back_to_entry_version_when_review_entry_id_is_missing(self):
        request = RequestFactory().post(
            "/verify-checked/",
            data=json.dumps(
                {
                    "field_template_ids": [11],
                    "review_entry_version": "1",
                    "review_page_status": "submitted",
                }
            ),
            content_type="application/json",
        )
        request.user = SimpleNamespace(id=7)

        with (
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "get_latest_submitted_page_entry_for_subject_visit_crf",
                return_value=SimpleNamespace(id=101, entry_version="1"),
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "merge_form_verification_checked_fields_into_page_state_final_data",
                return_value=(False, "under_review", [], []),
            ) as merge_checked,
        ):
            response = SubjectFormVerificationVerifyCheckedView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 200)
        merge_checked.assert_called_once()

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
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
                return_value=True,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "has_verified_reconcile_query_for_page_field",
            ) as has_verified_query,
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
        has_verified_query.assert_not_called()
        open_reconcile_query.assert_not_called()

    def test_post_returns_400_when_reconcile_query_is_verified(self):
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
                "get_page_state_status_for_subject_visit_crf",
                return_value="submitted",
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "is_field_verified_for_page_state",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "has_verified_reconcile_query_for_page_field",
                return_value=True,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
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
        self.assertEqual(payload["error"], ["Query đã được verify không thể tạo Query mới"])
        open_reconcile_query.assert_not_called()

    def test_query_thread_close_requires_resolved_flag(self):
        request = RequestFactory().post(
            "/query-thread/",
            data=json.dumps(
                {
                    "dataquery_id": 101,
                    "field_template_id": 11,
                    "message_text": "Close this query",
                    "close_query": True,
                    "is_resolved": False,
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
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked.reply_and_close_reconcile_query",
                side_effect=ValueError("Query must be resolved before it can be closed."),
            ) as reply_and_close,
        ):
            response = SubjectFormVerificationQueryThreadView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertEqual(payload["error"], ["Query must be resolved before it can be closed."])
        reply_and_close.assert_called_once_with(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            message_text="Close this query",
            actor_user_id=7,
            is_resolved=False,
        )

    def test_query_thread_close_passes_resolved_flag(self):
        request = RequestFactory().post(
            "/query-thread/",
            data=json.dumps(
                {
                    "dataquery_id": 101,
                    "field_template_id": 11,
                    "message_text": "Close this query",
                    "close_query": True,
                    "is_resolved": True,
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
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked.reply_and_close_reconcile_query",
                return_value={
                    "dataquery_id": 101,
                    "message_text": "Close this query",
                    "message_type": "resolution",
                    "created_at": created_at,
                    "closed": True,
                },
            ) as reply_and_close,
        ):
            response = SubjectFormVerificationQueryThreadView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertIs(payload["closed"], True)
        reply_and_close.assert_called_once_with(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            message_text="Close this query",
            actor_user_id=7,
            is_resolved=True,
        )

    def test_query_thread_allows_reply_and_close_for_any_study_user(self):
        request = RequestFactory().post(
            "/query-thread/",
            data=json.dumps(
                {
                    "dataquery_id": 101,
                    "field_template_id": 11,
                    "message_text": "Close this query",
                    "close_query": True,
                    "is_resolved": True,
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
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "reply_and_close_reconcile_query",
                return_value={
                    "dataquery_id": 101,
                    "message_text": "Close this query",
                    "message_type": "resolution",
                    "created_at": created_at,
                    "closed": True,
                },
            ) as reply_and_close,
        ):
            response = SubjectFormVerificationQueryThreadView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertIs(payload["closed"], True)
        reply_and_close.assert_called_once_with(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            message_text="Close this query",
            actor_user_id=7,
            is_resolved=True,
        )

    def test_query_thread_cancel_calls_cancel_reconcile_query(self):
        request = RequestFactory().post(
            "/query-thread/",
            data=json.dumps(
                {
                    "dataquery_id": 101,
                    "field_template_id": 11,
                    "cancel_query": True,
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
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked."
                "_current_user_matches_submitted_entry_editor",
                return_value=False,
            ),
            patch(
                "apps.subject.presentation.web.views.verification_verify_checked.cancel_reconcile_query",
                return_value={
                    "dataquery_id": 101,
                    "message_text": "",
                    "message_type": "cancelled",
                    "created_at": created_at,
                    "closed": False,
                    "cancelled": True,
                },
            ) as cancel_query,
        ):
            response = SubjectFormVerificationQueryThreadView().post(
                request,
                study_id=1,
                subject_id=2,
                visit_id=3,
                crf_template_id=4,
            )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertIs(payload["cancelled"], True)
        cancel_query.assert_called_once_with(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            actor_user_id=7,
        )

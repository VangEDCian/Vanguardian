from unittest.mock import patch

from django.test import SimpleTestCase

from apps.subject.application.services.form_field_review_table import FormFieldReviewTableService


class _NoQueryReadService:
    def count_open_queries_by_page_state_and_field_templates(self, **kwargs):
        return {}

    def list_field_template_ids_with_verified_queries(self, **kwargs):
        return set()

    def list_latest_active_query_ids_by_page_state_and_field_templates(self, **kwargs):
        return {}

    def list_latest_active_query_participants_by_page_state_and_field_templates(self, **kwargs):
        return {}

    def list_latest_active_query_answered_flags_by_page_state_and_field_templates(self, **kwargs):
        return {}

    def count_query_threads_since_current_user_last_comment(self, **kwargs):
        return {}

    def list_latest_query_messages_by_page_state_and_field_templates(self, **kwargs):
        return {}

    def list_closed_query_histories_by_page_state_and_field_templates(self, **kwargs):
        return {}


class FormFieldReviewTableServiceTests(SimpleTestCase):
    def test_radio_display_value_uses_static_option_label(self):
        result = self._build_review_rows(
            field_templates_payload=[
                {
                    "id": 11,
                    "field_key": "sex",
                    "label": "Sex",
                    "ui_config": {
                        "control_type": "radio",
                        "options": {
                            "source": "static",
                            "static": [
                                {"value": "M", "label": "Male"},
                                {"value": "F", "label": "Female"},
                            ],
                        },
                    },
                },
            ],
            entry_payload={"sex": "F"},
        )

        self.assertEqual(result[0]["display_value"], "Female")

    def test_checkbox_display_value_uses_static_option_labels(self):
        result = self._build_review_rows(
            field_templates_payload=[
                {
                    "id": 12,
                    "field_key": "symptoms",
                    "label": "Symptoms",
                    "ui_config": {
                        "control_type": "checkbox",
                        "options": {
                            "source": "static",
                            "static": [
                                {"value": "headache", "label": "Headache"},
                                {"value": "nausea", "label": "Nausea"},
                            ],
                        },
                    },
                },
            ],
            entry_payload={"symptoms": ["headache", "nausea"]},
        )

        self.assertEqual(result[0]["display_value"], "Headache, Nausea")

    def test_sets_verified_query_flag_from_reconcile_query_status(self):
        service = FormFieldReviewTableService(reconcile_read_service=_VerifiedQueryReadService())
        with patch(
            "apps.subject.application.services.form_field_review_table."
            "DjangoSubjectEventInstanceScheduleReadRepository.get_event_start_datetime",
            return_value=None,
        ):
            review = service.build_for_verification(
                subject_code="S-001",
                site_id=1,
                event_name="Visit 1",
                event_instance_id=1,
                form_name="Vitals",
                form_status="submitted",
                entry_version="1",
                entry_updated_at=None,
                entry_updated_by_id=None,
                field_templates_payload=[
                    {
                        "id": 11,
                        "field_key": "sex",
                        "label": "Sex",
                    },
                    {
                        "id": 12,
                        "field_key": "symptoms",
                        "label": "Symptoms",
                    },
                ],
                entry_payload={},
                page_state_id=23,
            )

        self.assertIs(review["rows"][0]["has_verified_query"], True)
        self.assertIs(review["rows"][1]["has_verified_query"], False)

    def test_sets_closed_query_histories_from_reconcile_query_status(self):
        service = FormFieldReviewTableService(reconcile_read_service=_ClosedQueryHistoryReadService())
        with patch(
            "apps.subject.application.services.form_field_review_table."
            "DjangoSubjectEventInstanceScheduleReadRepository.get_event_start_datetime",
            return_value=None,
        ):
            review = service.build_for_verification(
                subject_code="S-001",
                site_id=1,
                event_name="Visit 1",
                event_instance_id=1,
                form_name="Vitals",
                form_status="submitted",
                entry_version="1",
                entry_updated_at=None,
                entry_updated_by_id=None,
                field_templates_payload=[
                    {
                        "id": 11,
                        "field_key": "sex",
                        "label": "Sex",
                    },
                ],
                entry_payload={},
                page_state_id=23,
            )

        history = review["rows"][0]["closed_query_histories"][0]
        self.assertEqual(history["dataquery_id"], 201)
        self.assertEqual(history["label"], "Query #201")
        self.assertEqual(history["messages"][0]["text"], "Closed message")

    def test_sets_active_query_answered_flag_from_reconcile_query(self):
        service = FormFieldReviewTableService(reconcile_read_service=_AnsweredQueryReadService())
        with patch(
            "apps.subject.application.services.form_field_review_table."
            "DjangoSubjectEventInstanceScheduleReadRepository.get_event_start_datetime",
            return_value=None,
        ):
            review = service.build_for_verification(
                subject_code="S-001",
                site_id=1,
                event_name="Visit 1",
                event_instance_id=1,
                form_name="Vitals",
                form_status="submitted",
                entry_version="1",
                entry_updated_at=None,
                entry_updated_by_id=None,
                field_templates_payload=[
                    {
                        "id": 11,
                        "field_key": "sex",
                        "label": "Sex",
                    },
                ],
                entry_payload={},
                page_state_id=23,
            )

        self.assertIs(review["rows"][0]["active_query_is_answered"], True)

    def test_sets_active_query_can_respond_for_query_participants(self):
        service = FormFieldReviewTableService(reconcile_read_service=_ParticipantQueryReadService())
        with patch(
            "apps.subject.application.services.form_field_review_table."
            "DjangoSubjectEventInstanceScheduleReadRepository.get_event_start_datetime",
            return_value=None,
        ):
            review = service.build_for_verification(
                subject_code="S-001",
                site_id=1,
                event_name="Visit 1",
                event_instance_id=1,
                form_name="Vitals",
                form_status="submitted",
                entry_version="1",
                entry_updated_at=None,
                entry_updated_by_id=None,
                field_templates_payload=[
                    {
                        "id": 11,
                        "field_key": "sex",
                        "label": "Sex",
                    },
                    {
                        "id": 12,
                        "field_key": "symptoms",
                        "label": "Symptoms",
                    },
                ],
                entry_payload={},
                page_state_id=23,
                current_user_id=7,
            )

        self.assertIs(review["rows"][0]["active_query_can_respond"], True)
        self.assertIs(review["rows"][1]["active_query_can_respond"], False)

    @staticmethod
    def _build_review_rows(*, field_templates_payload, entry_payload):
        service = FormFieldReviewTableService(reconcile_read_service=_NoQueryReadService())
        with patch(
            "apps.subject.application.services.form_field_review_table."
            "DjangoSubjectEventInstanceScheduleReadRepository.get_event_start_datetime",
            return_value=None,
        ):
            review = service.build_for_verification(
                subject_code="S-001",
                site_id=1,
                event_name="Visit 1",
                event_instance_id=1,
                form_name="Vitals",
                form_status="submitted",
                entry_version="1",
                entry_updated_at=None,
                entry_updated_by_id=None,
                field_templates_payload=field_templates_payload,
                entry_payload=entry_payload,
                page_state_id=None,
            )
        return review["rows"]


class _VerifiedQueryReadService(_NoQueryReadService):
    def list_field_template_ids_with_verified_queries(self, **kwargs):
        return {11}


class _ClosedQueryHistoryReadService(_NoQueryReadService):
    def list_closed_query_histories_by_page_state_and_field_templates(self, **kwargs):
        return {
            11: [
                {
                    "dataquery_id": 201,
                    "question_text": "Old query",
                    "opened_at": None,
                    "closed_at": None,
                    "messages": [
                        {
                            "dataquery_id": 201,
                            "text": "Closed message",
                            "status": "comment",
                            "created_at": None,
                            "opened_by_id": None,
                        },
                    ],
                },
            ],
        }


class _AnsweredQueryReadService(_NoQueryReadService):
    def list_latest_active_query_ids_by_page_state_and_field_templates(self, **kwargs):
        return {11: 101}

    def list_latest_active_query_answered_flags_by_page_state_and_field_templates(self, **kwargs):
        return {11: True}


class _ParticipantQueryReadService(_NoQueryReadService):
    def list_latest_active_query_ids_by_page_state_and_field_templates(self, **kwargs):
        return {11: 101, 12: 102}

    def list_latest_active_query_participants_by_page_state_and_field_templates(self, **kwargs):
        return {
            11: {"opened_by_id": 7, "assigned_to_id": 9},
            12: {"opened_by_id": 8, "assigned_to_id": 9},
        }

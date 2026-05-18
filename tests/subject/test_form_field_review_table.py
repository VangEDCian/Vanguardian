from unittest.mock import patch

from django.test import SimpleTestCase

from apps.subject.application.services.form_field_review_table import FormFieldReviewTableService


class _NoQueryReadService:
    def count_open_queries_by_page_state_and_field_templates(self, **kwargs):
        return {}

    def list_latest_active_query_ids_by_page_state_and_field_templates(self, **kwargs):
        return {}

    def count_query_threads_since_current_user_last_comment(self, **kwargs):
        return {}

    def list_latest_query_messages_by_page_state_and_field_templates(self, **kwargs):
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

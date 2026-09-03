from datetime import datetime, timezone

from django.test import SimpleTestCase

from apps.datacapture.application.services.page_state_audit_history import (
    DataCapturePageStateAuditHistoryService,
)


class DataCapturePageStateAuditHistoryServiceTests(SimpleTestCase):
    def test_list_for_subject_normalizes_page_state_transition_rows(self):
        service = DataCapturePageStateAuditHistoryService(repository=_PageStateAuditRepositoryStub())

        records = service.list_for_subject(subject_id=20, limit=25, search="nguyen", field_name="status")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["category"], "page_state")
        self.assertEqual(records[0]["scope"], "Baseline / VITALS / Repeat 2")
        self.assertEqual(records[0]["from_value"], "Draft")
        self.assertEqual(records[0]["to_value"], "Submitted")
        self.assertEqual(records[0]["actor"], "User #11")
        self.assertEqual(records[0]["field_name"], "page_state_status")
        self.assertEqual(records[0]["field_description"], "Baseline / VITALS")
        self.assertEqual(records[0]["value"], "Draft Submitted")
        self.assertEqual(records[0]["user_display"], "User #11")
        self.assertEqual(records[0]["reason"], "Submit Reason: Investigator submitted")
        self.assertEqual(service.repository.kwargs["search"], "nguyen")
        self.assertEqual(service.repository.kwargs["field_name"], "status")


class _PageStateAuditRepositoryStub:
    def __init__(self):
        self.kwargs = None

    def list_page_state_transition_history_for_subject(self, *, subject_id, limit, search="", field_name=""):
        self.kwargs = {"search": search, "field_name": field_name}
        return [
            {
                "occurred_at": datetime(2026, 6, 3, 9, 0, tzinfo=timezone.utc),
                "field_name": "page_state_status",
                "field_description": "Baseline / VITALS",
                "value": "Draft Submitted",
                "user_display": "User #11",
                "page_state_id": 300,
                "from_status": "draft",
                "to_status": "submitted",
                "data_version": 2,
                "reason_code": "submit_reason",
                "reason_text": "Investigator submitted",
                "trigger_source": "user",
                "actor_id": 11,
                "event_code": "BASELINE",
                "event_label": "Baseline",
                "form_code": "VITALS",
                "form_label": "VITALS",
                "repeat_index": 2,
            }
        ]

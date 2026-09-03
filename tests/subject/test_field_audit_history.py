from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from apps.core.choices import DataCapturePageEntryStatusChoices
from apps.datacapture.infrastructure.persistence.models import DataCapturePageEntry
from apps.subject.application.services.field_audit_history import SubjectFieldAuditHistoryQueryService
from apps.subject.infrastructure.repositories.field_audit_history import DjangoSubjectFieldAuditHistoryRepository
from apps.subject.presentation.web.views.field_audit_history import SubjectFieldAuditHistoryView


class SubjectFieldAuditHistoryTests(SimpleTestCase):
    def test_audit_history_url_routes_to_subject_field_audit_history_view(self):
        url = reverse(
            "subject:subject_field_audit_history",
            kwargs={
                "study_id": 1,
                "subject_id": 20,
                "visit_id": 30,
                "crf_template_id": 40,
            },
        )

        match = resolve(url)

        self.assertEqual(match.func.view_class, SubjectFieldAuditHistoryView)

    def test_get_field_audit_history_returns_none_when_subject_is_missing(self):
        service = SubjectFieldAuditHistoryQueryService(repository=_MissingSubjectFieldAuditHistoryRepositoryStub())

        self.assertIsNone(
            service.get_field_audit_history(
                study_id=1,
                subject_id=20,
                visit_id=30,
                crf_template_id=40,
                field_template_id=50,
                field_key="VISIT_DATE",
            )
        )

    def test_get_field_audit_history_wraps_repository_rows(self):
        repository = _SubjectFieldAuditHistoryRepositoryStub()
        service = SubjectFieldAuditHistoryQueryService(repository=repository)

        result = service.get_field_audit_history(
            study_id=1,
            subject_id=20,
            visit_id=30,
            crf_template_id=40,
            field_template_id=50,
            field_key="VISIT_DATE",
            event_form_binding_id=7,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "AUDIT HISTORY")
        self.assertEqual(result["total_count"], 2)
        self.assertEqual(repository.subject_kwargs, {"study_id": 1, "subject_id": 20})
        self.assertEqual(
            repository.history_kwargs,
            {
                "study_id": 1,
                "subject_id": 20,
                "visit_id": 30,
                "crf_template_id": 40,
                "field_template_id": 50,
                "field_key": "VISIT_DATE",
                "event_form_binding_id": 7,
                "limit": 100,
            },
        )
        self.assertEqual(result["rows"][0]["audit_event"], "Item data value updated")

    def test_field_render_renders_audit_history_button(self):
        rendered = render_to_string(
            "subject/components/_field_render.html",
            {
                "field_audit_history_url": "/subjects/1/audit-history/",
                "field": {
                    "id": 50,
                    "field_key": "VISIT_DATE",
                    "label": "Visit Date",
                    "control_type": "text",
                    "value": "2021-02-26",
                    "display_value": "26-02-2021",
                },
            },
        )

        self.assertIn("data-field-audit-history-modal-trigger", rendered)
        self.assertIn("images/datacapture/history.svg", rendered)

    def test_format_datetime_localizes_aware_datetime_to_current_timezone(self):
        repository = DjangoSubjectFieldAuditHistoryRepository()

        self.assertEqual(
            repository._format_datetime(datetime(2026, 6, 30, 8, 16, tzinfo=timezone.utc)),
            "30-06-2026 15:16",
        )

    def test_page_entry_audit_excludes_draft_entries(self):
        repository = DjangoSubjectFieldAuditHistoryRepository()
        queryset = MagicMock()
        queryset.exclude.return_value.only.return_value.order_by.return_value = []

        with patch.object(DataCapturePageEntry.objects, "filter", return_value=queryset) as filter_mock:
            repository._build_page_entry_rows(page_state_id=123, field_key="ICF_DATE", user_display_by_id={})

        filter_mock.assert_called_once_with(page_state_id=123, deleted=False)
        queryset.exclude.assert_called_once_with(status=DataCapturePageEntryStatusChoices.DRAFT)

class _SubjectFieldAuditHistoryRepositoryStub:
    def __init__(self):
        self.subject_kwargs = None
        self.history_kwargs = None

    def get_subject_context(self, *, study_id, subject_id):
        self.subject_kwargs = {"study_id": study_id, "subject_id": subject_id}
        return {
            "subject_id": subject_id,
            "study_id": study_id,
            "study_code": "NNG31",
            "study_name": "NNG31 Study",
            "site_code": "SITE01",
            "screening_code": "SCR-001",
            "subject_code": "SUBJ-001",
        }

    def list_field_audit_history(
        self,
        *,
        study_id,
        subject_id,
        visit_id,
        crf_template_id,
        field_template_id,
        field_key,
        limit,
        event_form_binding_id=None,
    ):
        self.history_kwargs = {
            "study_id": study_id,
            "subject_id": subject_id,
            "visit_id": visit_id,
            "crf_template_id": crf_template_id,
            "field_template_id": field_template_id,
            "field_key": field_key,
            "event_form_binding_id": event_form_binding_id,
            "limit": limit,
        }
        return [
            {
                "audit_event": "Item data value updated",
                "changed_at": "26-06-2022 08:16",
                "changed_by": "phuongtran",
                "field_name": "VISIT_DATE",
                "value_from": "26-02-2021",
                "value_to": "26-03-2021",
            },
            {
                "audit_event": "Item Data SDV Status Updated",
                "changed_at": "26-06-2022 08:16",
                "changed_by": "phuongtran",
                "field_name": "VISIT_DATE",
                "value_from": "Verified",
                "value_to": "Not Verified",
            },
        ]


class _MissingSubjectFieldAuditHistoryRepositoryStub(_SubjectFieldAuditHistoryRepositoryStub):
    def get_subject_context(self, *, study_id, subject_id):
        self.subject_kwargs = {"study_id": study_id, "subject_id": subject_id}
        return None

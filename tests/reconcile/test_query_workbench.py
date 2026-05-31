from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from apps.reconcile.application.services.query_workbench import QueryWorkbenchReader
from apps.reconcile.presentation.web.views import QueryWorkbenchView


class QueryWorkbenchReaderTests(SimpleTestCase):
    def test_pending_with_maps_status_to_responsible_party(self):
        self.assertEqual(QueryWorkbenchReader.pending_with("open"), "Site / Data Entry")
        self.assertEqual(QueryWorkbenchReader.pending_with("reopened"), "Site / Data Entry")
        self.assertEqual(QueryWorkbenchReader.pending_with("answered"), "CRA / Data Manager")
        self.assertEqual(QueryWorkbenchReader.pending_with("resolved"), "Data Manager / Close")
        self.assertEqual(QueryWorkbenchReader.pending_with("closed"), "—")

    def test_reader_builds_summary_items_and_validation_issues_from_scoped_context(self):
        contexts = {
            10: SimpleNamespace(
                page_state_id=10,
                study_id=1,
                site_id=2,
                subject_id=3,
                subject_code="SUBJ-001",
                screening_code="SCR-001",
                event_instance_id=4,
                event_code="VISIT1",
                event_label="Visit 1",
                crf_page_label="Vitals",
                page_template_id=5,
            )
        }
        repository = _WorkbenchRepository()
        with patch(
            "apps.datacapture.public.list_page_state_contexts_for_study_site",
            return_value=contexts,
        ):
            result = QueryWorkbenchReader(repository=repository).read(
                study_id=1,
                site_id=2,
                current_user_id=9,
                can_view_internal_thread=False,
                bucket="validation_issues",
            )

        self.assertEqual(result.summary.open, 1)
        self.assertEqual(result.summary.awaiting_site_response, 2)
        self.assertEqual(result.summary.awaiting_review, 1)
        self.assertEqual(result.summary.blocking_open, 1)
        self.assertEqual(result.summary.closed, 0)
        self.assertEqual(result.items, [])
        self.assertEqual(result.validation_issues[0].subject_code, "SUBJ-001")

    def test_reader_maps_query_row_context_and_reply_count(self):
        contexts = {
            10: SimpleNamespace(
                page_state_id=10,
                study_id=1,
                site_id=2,
                subject_id=3,
                subject_code="SUBJ-001",
                screening_code="SCR-001",
                event_instance_id=4,
                event_code="VISIT1",
                event_label="Visit 1",
                crf_page_label="Vitals",
                page_template_id=5,
            )
        }
        repository = _WorkbenchRepository(
            rows=[
                {
                    "query_id": 11,
                    "page_state_id": 10,
                    "status": "answered",
                    "source": "manual",
                    "query_type": "manual",
                    "severity": "major",
                    "is_blocking": True,
                    "question_text": "Please confirm the weight value",
                    "resolution_note": "",
                    "field_path": "$.weight",
                    "value_snapshot": "72",
                    "opened_at": None,
                    "answered_at": None,
                    "resolved_at": None,
                    "closed_at": None,
                    "last_activity_at": None,
                    "reply_count": 3,
                    "assigned_to_id": 8,
                    "opened_by_id": 9,
                    "field_label": "Weight",
                }
            ]
        )
        with patch(
            "apps.datacapture.public.list_page_state_contexts_for_study_site",
            return_value=contexts,
        ):
            result = QueryWorkbenchReader(repository=repository).read(
                study_id=1,
                site_id=2,
                current_user_id=9,
                can_view_internal_thread=False,
                bucket="awaiting_review",
                assigned_to_id=9,
                opened_by_id=9,
            )

        self.assertEqual(repository.last_query_kwargs["bucket"], "awaiting_review")
        self.assertEqual(repository.last_query_kwargs["assigned_to_id"], 9)
        self.assertEqual(repository.last_query_kwargs["opened_by_id"], 9)
        self.assertEqual(result.items[0].pending_with, "CRA / Data Manager")
        self.assertEqual(result.items[0].reply_count, 3)
        self.assertEqual(result.items[0].subject_code, "SUBJ-001")
        self.assertEqual(result.items[0].field_label_or_path, "Weight")

    def test_reconcile_application_uses_datacapture_public_contract(self):
        source = Path("src/apps/reconcile/application/services/query_workbench.py").read_text()

        self.assertIn("from apps.datacapture.public import", source)
        self.assertNotIn("apps.datacapture.models", source)
        self.assertNotIn("apps.datacapture.infrastructure", source)


class QueryWorkbenchRoutingTests(SimpleTestCase):
    def test_query_workbench_route_resolves(self):
        match = resolve(reverse("reconcile:query_workbench", kwargs={"study_id": 1}))

        self.assertEqual(match.func.view_class, QueryWorkbenchView)

    def test_query_nav_is_rendered_after_subjects(self):
        layout_source = Path("src/templates/shared/_layout.html").read_text()

        subject_index = layout_source.index("layout_nav_permissions.subjects")
        query_index = layout_source.index("layout_nav_permissions.queries")
        sites_index = layout_source.index("layout_nav_permissions.sites")
        self.assertLess(subject_index, query_index)
        self.assertLess(query_index, sites_index)


class _WorkbenchRepository:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.last_query_kwargs = None

    def summarize_workbench(self, *, page_state_ids):
        return {
            "total": 4,
            "open": 1,
            "awaiting_site_response": 2,
            "awaiting_review": 1,
            "blocking_open": 1,
            "resolved": 1,
            "closed": 0,
            "validation_issues_open": 1,
            "actionable_for_current_user": 3,
        }

    def list_workbench_queries(self, **kwargs):
        self.last_query_kwargs = kwargs
        if kwargs["bucket"] == "validation_issues":
            return []
        return self.rows

    def list_workbench_validation_issues(self, **kwargs):
        return [
            {
                "issue_id": 7,
                "page_state_id": 10,
                "status": "OPEN",
                "severity": "major",
                "message": "Required value is missing",
                "failed_value": None,
                "created_at": None,
                "resolved_at": None,
            }
        ]

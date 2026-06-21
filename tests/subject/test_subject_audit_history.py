from datetime import datetime, timezone
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from apps.subject.application.services.audit_history import SubjectAuditHistoryQueryService
from apps.subject.presentation.web.views.audit_history import SubjectAuditHistoryView


class SubjectAuditHistoryQueryServiceTests(SimpleTestCase):
    def test_audit_history_url_routes_to_subject_audit_history_view(self):
        url = reverse("subject:subject_audit_history", kwargs={"study_id": 1, "subject_id": 20})

        match = resolve(url)

        self.assertEqual(match.func.view_class, SubjectAuditHistoryView)

    def test_audit_history_template_uses_query_workbench_table_layout(self):
        template_source = Path("src/templates/subject/subject_audit_history.html").read_text()

        self.assertIn("query-workbench subject-audit-workbench", template_source)
        self.assertIn("{% render_table table %}", template_source)
        self.assertIn("filter_form.field_name", template_source)
        self.assertIn("filter_form.search", template_source)

    def test_audit_history_search_uses_mariadb_compatible_audit_fields(self):
        sources = "\n".join(
            Path(path).read_text()
            for path in (
                "src/apps/subject/infrastructure/repositories/audit_history.py",
                "src/apps/datacapture/infrastructure/repositories/page_capture.py",
                "src/apps/study/infrastructure/repositories/event_gate.py",
            )
        )

        self.assertNotIn("django.contrib.postgres.search", sources)
        self.assertIn("audit_value__icontains", sources)
        self.assertIn("audit_field_description__icontains", sources)
        self.assertIn("audit_user_display__icontains", sources)

    def test_get_subject_audit_history_combines_sources_and_sorts_latest_first(self):
        repository = _SubjectAuditHistoryRepositoryStub()
        datacapture_reader = _PageStateHistoryReaderStub()
        study_gate_reader = _EventGateHistoryReaderStub()
        service = SubjectAuditHistoryQueryService(
            repository=repository,
            datacapture_history_reader=datacapture_reader,
            study_gate_history_reader=study_gate_reader,
        )

        result = service.get_subject_audit_history(
            study_id=1,
            subject_id=20,
            search="nguyen",
            field_name="status",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "SUBJ-001")
        self.assertEqual(result["total_count"], 4)
        self.assertEqual(
            [record["source"] for record in result["records"]],
            ["Event Gate", "Page State", "Event Transition", "Subject Status"],
        )
        self.assertEqual(
            {item["key"]: item["count"] for item in result["source_counts"]},
            {
                "subject_status": 1,
                "event_transition": 1,
                "page_state": 1,
                "event_gate": 1,
            },
        )
        self.assertEqual(result["records"][0]["to_value"], "Fail")
        self.assertEqual(result["records"][0]["field_name"], "baseline_ready")
        self.assertEqual(result["records"][0]["user_display"], "System")
        self.assertEqual(repository.status_kwargs["search"], "nguyen")
        self.assertEqual(repository.status_kwargs["field_name"], "status")
        self.assertEqual(datacapture_reader.kwargs["search"], "nguyen")
        self.assertEqual(study_gate_reader.kwargs["field_name"], "status")

    def test_get_subject_audit_history_returns_none_when_subject_is_missing(self):
        service = SubjectAuditHistoryQueryService(
            repository=_MissingSubjectAuditHistoryRepositoryStub(),
            datacapture_history_reader=_PageStateHistoryReaderStub(),
            study_gate_history_reader=_EventGateHistoryReaderStub(),
        )

        self.assertIsNone(service.get_subject_audit_history(study_id=1, subject_id=999))


class _SubjectAuditHistoryRepositoryStub:
    def __init__(self):
        self.status_kwargs = None
        self.event_kwargs = None

    def get_subject_context(self, *, study_id, subject_id, snapshot_class):
        return snapshot_class(
            subject_id=subject_id,
            study_id=study_id,
            study_code="NNG31",
            study_name="NNG31 Study",
            site_code="SITE01",
            screening_code="SCR-001",
            subject_code="SUBJ-001",
        )

    def list_subject_status_history(self, *, subject_id, record_class, limit, search="", field_name=""):
        self.status_kwargs = {"search": search, "field_name": field_name}
        return [
            record_class(
                occurred_at=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
                field_name="subject_status",
                field_description="Subject status transition",
                value="Screening Enrolled Subject enrolled",
                user_display="Nguyen CRC",
                from_status="screening",
                to_status="enrolled",
                reason_code="eligible",
                reason_text="Subject enrolled",
                source="user",
                actor_id=10,
            )
        ]

    def list_event_instance_transition_history(
        self,
        *,
        study_id,
        subject_id,
        record_class,
        limit,
        search="",
        field_name="",
    ):
        self.event_kwargs = {"search": search, "field_name": field_name}
        return [
            record_class(
                occurred_at=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
                field_name="event_transition",
                field_description="Screening -> Baseline",
                value="Completed Open All required forms submitted",
                user_display="System",
                from_event_label="Screening",
                to_event_label="Baseline",
                from_status="completed",
                to_status="open",
                trigger_source="datacapture",
                result="applied",
                reason="All required forms submitted",
                actor_id=None,
                transition_rule_id=7,
            )
        ]


class _MissingSubjectAuditHistoryRepositoryStub(_SubjectAuditHistoryRepositoryStub):
    def get_subject_context(self, *, study_id, subject_id, snapshot_class):
        return None


class _PageStateHistoryReaderStub:
    def __init__(self):
        self.kwargs = None

    def __call__(self, *, subject_id, limit, search="", field_name=""):
        self.kwargs = {"search": search, "field_name": field_name}
        return [
            {
                "occurred_at": datetime(2026, 6, 3, 9, 0, tzinfo=timezone.utc),
                "category": "page_state",
                "source": "Page State",
                "field_name": "page_state_status",
                "field_description": "Baseline / VITALS",
                "value": "Draft Submitted",
                "user_display": "User #11",
                "scope": "Baseline / VITALS",
                "action": "Page state transition",
                "from_value": "Draft",
                "to_value": "Submitted",
                "actor": "User #11",
                "reason": "",
                "details": [{"label": "Trigger Source", "value": "User"}],
            }
        ]


class _EventGateHistoryReaderStub:
    def __init__(self):
        self.kwargs = None

    def __call__(self, *, study_id, subject_id, limit, search="", field_name=""):
        self.kwargs = {"search": search, "field_name": field_name}
        return [
            {
                "occurred_at": datetime(2026, 6, 4, 9, 0, tzinfo=timezone.utc),
                "category": "event_gate",
                "source": "Event Gate",
                "field_name": "baseline_ready",
                "field_description": "Baseline / Open Event",
                "value": "Fail Missing baseline facts",
                "user_display": "System",
                "scope": "Baseline",
                "action": "Open Event",
                "from_value": "Transition",
                "to_value": "Fail",
                "actor": "System",
                "reason": "Missing baseline facts",
                "details": [{"label": "Gate Code", "value": "baseline_ready"}],
            }
        ]

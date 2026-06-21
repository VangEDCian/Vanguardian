from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.presentation.web.tables import SubjectAuditHistoryTable, SubjectListTable


class SubjectListTableTests(SimpleTestCase):
    def test_subject_audit_history_table_has_workbench_columns(self):
        table = SubjectAuditHistoryTable([])

        self.assertEqual(
            table.columns.names(),
            [
                "occurred_at",
                "source",
                "field_name",
                "field_description",
                "value",
                "user_display",
                "details",
            ],
        )

    def test_subject_list_table_shows_arm_after_randomization(self):
        record = SimpleNamespace(
            pk=1,
            study_id=10,
            subject_code="SUBJ-001",
            screening_code="SCR-001",
            created_at=None,
            randomization=SimpleNamespace(
                created_at=None,
                arm=SimpleNamespace(arm_name="Eprex -> NANOKINE"),
            ),
            open_query_count=3,
            validation_issue_count=2,
        )
        table = SubjectListTable(
            [record],
            verify_show_by_subject_id={},
            workflow_action_event_id_by_subject_id={},
            can_update_subject=False,
        )

        self.assertIn("arm", table.columns.names())
        self.assertIn("open_queries", table.columns.names())
        self.assertIn("validation_issues", table.columns.names())
        self.assertNotIn("query_status", table.columns.names())
        self.assertLess(table.columns.names().index("randomization"), table.columns.names().index("arm"))
        self.assertLess(table.columns.names().index("arm"), table.columns.names().index("completion"))
        self.assertEqual(str(table.columns["arm"].header), "ARM")
        self.assertEqual(str(table.columns["open_queries"].header), "Open Queries")
        self.assertEqual(str(table.columns["validation_issues"].header), "Validation Issues")
        self.assertEqual(table.render_arm(record), "Eprex -> NANOKINE")
        self.assertEqual(table.render_open_queries(record), 3)
        self.assertEqual(table.render_validation_issues(record), 2)

    def test_subject_list_table_arm_falls_back_to_dash_when_missing(self):
        record = SimpleNamespace(randomization=SimpleNamespace(arm=None))
        table = SubjectListTable(
            [record],
            verify_show_by_subject_id={},
            workflow_action_event_id_by_subject_id={},
            can_update_subject=False,
        )

        self.assertEqual(table.render_arm(record), "—")

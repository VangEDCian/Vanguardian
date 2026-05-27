from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.presentation.web.tables import SubjectListTable


class SubjectListTableTests(SimpleTestCase):
    def test_subject_list_table_renames_query_status_and_shows_validation_issues(self):
        record = SimpleNamespace(
            pk=1,
            study_id=10,
            subject_code="SUBJ-001",
            screening_code="SCR-001",
            created_at=None,
            open_query_count=3,
            validation_issue_count=2,
        )
        table = SubjectListTable(
            [record],
            verify_show_by_subject_id={},
            workflow_action_event_id_by_subject_id={},
            can_update_subject=False,
        )

        self.assertIn("open_queries", table.columns.names())
        self.assertIn("validation_issues", table.columns.names())
        self.assertNotIn("query_status", table.columns.names())
        self.assertEqual(str(table.columns["open_queries"].header), "Open Queries")
        self.assertEqual(str(table.columns["validation_issues"].header), "Validation Issues")
        self.assertEqual(table.render_open_queries(record), 3)
        self.assertEqual(table.render_validation_issues(record), 2)

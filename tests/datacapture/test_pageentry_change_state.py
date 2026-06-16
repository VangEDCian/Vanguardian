from django.test import SimpleTestCase

from apps.datacapture.domain import PageEntryChangeState, PageEntryChangeStateResult
from apps.datacapture.domain.exceptions import UnsupportedEntryStatusError
from apps.datacapture.domain.status import DataCapturePageEntry


class PageEntryChangeStateTests(SimpleTestCase):
    def test_create_draft_returns_draft_status(self):
        result = PageEntryChangeState.create_draft()

        self.assertEqual(
            result,
            PageEntryChangeStateResult(
                from_status=None,
                to_status=DataCapturePageEntry.DRAFT,
            ),
        )
        self.assertIs(result.changed, True)

    def test_create_submitted_returns_submitted_status(self):
        result = PageEntryChangeState.create_submitted()

        self.assertEqual(result.to_status, DataCapturePageEntry.SUBMITTED)
        self.assertIs(result.changed, True)

    def test_state_change_result_builds_changed_event(self):
        result = PageEntryChangeState.submit(DataCapturePageEntry.DRAFT)

        event = result.to_event(
            entry_id=10,
            page_state_id=20,
            subject_id=30,
            visit_id=40,
            crf_template_id=50,
            actor_user_id=60,
        )

        self.assertEqual(event.entry_id, 10)
        self.assertEqual(event.from_status, DataCapturePageEntry.DRAFT)
        self.assertEqual(event.to_status, DataCapturePageEntry.SUBMITTED)
        self.assertEqual(event.actor_user_id, 60)

    def test_submit_changes_draft_to_submitted(self):
        result = PageEntryChangeState.submit(DataCapturePageEntry.DRAFT)

        self.assertEqual(result.from_status, DataCapturePageEntry.DRAFT)
        self.assertEqual(result.to_status, DataCapturePageEntry.SUBMITTED)
        self.assertIs(result.changed, True)

    def test_supersede_changes_submitted_to_superseded(self):
        result = PageEntryChangeState.supersede(DataCapturePageEntry.SUBMITTED)

        self.assertEqual(result.from_status, DataCapturePageEntry.SUBMITTED)
        self.assertEqual(result.to_status, DataCapturePageEntry.SUPERSEDED)

    def test_cancel_changes_draft_to_cancelled(self):
        result = PageEntryChangeState.cancel(DataCapturePageEntry.DRAFT)

        self.assertEqual(result.from_status, DataCapturePageEntry.DRAFT)
        self.assertEqual(result.to_status, DataCapturePageEntry.CANCELLED)

    def test_rejects_invalid_transition_status(self):
        with self.assertRaises(UnsupportedEntryStatusError):
            PageEntryChangeState.submit(DataCapturePageEntry.SUBMITTED)

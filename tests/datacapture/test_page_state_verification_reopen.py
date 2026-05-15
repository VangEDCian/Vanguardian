from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.datacapture.application.exceptions import (
    DataCapturePageReopenReasonRequiredError,
    DataCapturePageVerifyStateError,
)
from apps.datacapture.application.services.page_state_verification_final_data import (
    DataCapturePageStateVerificationFinalDataService,
)
from apps.datacapture.domain import DataCapturePageEntry, DataCapturePageState
from apps.datacapture.infrastructure.models.capture import (
    DataCapturePageEntrySnapshot,
    DataCapturePageStateSnapshot,
)


class _NoBlockingQueries:
    def has_active_blocking_query_for_page_field(self, **kwargs):
        return False

    def has_active_blocking_query_for_page(self, **kwargs):
        return False


class _CorrectionRequiredVerificationRepository:
    def __init__(self):
        self.status = DataCapturePageState.CORRECTION_REQUIRED
        self.start_page_review_called = False
        self.verify_page_state_if_ready_called = False

    def get_page_state(self, **kwargs):
        return DataCapturePageStateSnapshot(
            id=11,
            status=self.status,
            final_data="{}",
            data_version=3,
            current_entry_id=21,
            crf_template_id=31,
            subject_id=41,
            visit_id=51,
            study_id=61,
            study_version="1",
            event_definition_id=71,
        )

    def start_page_review(self, **kwargs):
        self.start_page_review_called = True
        self.status = DataCapturePageState.UNDER_REVIEW
        return SimpleNamespace(pk=11)

    def ensure_field_reviews_for_page(self, **kwargs):
        return 1

    def get_current_entry(self, **kwargs):
        return DataCapturePageEntrySnapshot(
            id=21,
            page_state_id=11,
            parent_entry_id=None,
            entry_no=1,
            entry_kind="initial",
            entry_version="1.0",
            status=DataCapturePageEntry.SUBMITTED,
            data='{"field_1": "value"}',
            crf_template_id=31,
            subject_id=41,
            visit_id=51,
        )

    def verify_field_review(self, **kwargs):
        return None

    def find_page_verification_field_review_blockers(self, **kwargs):
        return []

    def verify_page_state_if_ready(self, **kwargs):
        self.verify_page_state_if_ready_called = True
        self.status = DataCapturePageState.VERIFIED
        return DataCapturePageState.VERIFIED


class _VerifiedReopenRepository:
    def __init__(self):
        self.reopen_kwargs = None

    def get_page_state(self, **kwargs):
        return DataCapturePageStateSnapshot(
            id=12,
            status=DataCapturePageState.VERIFIED,
            final_data="{}",
            data_version=3,
            current_entry_id=21,
            crf_template_id=31,
            subject_id=41,
            visit_id=51,
            study_id=61,
            study_version="1",
            event_definition_id=71,
        )

    def reopen_verified_page_state(self, **kwargs):
        self.reopen_kwargs = kwargs
        return DataCapturePageState.CORRECTION_REQUIRED


class _NotReviewableVerificationRepository:
    def __init__(self, *, status):
        self.status = status
        self.start_page_review_called = False

    def get_page_state(self, **kwargs):
        return DataCapturePageStateSnapshot(
            id=13,
            status=self.status,
            final_data="{}",
            data_version=3,
            current_entry_id=21,
            crf_template_id=31,
            subject_id=41,
            visit_id=51,
            study_id=61,
            study_version="1",
            event_definition_id=71,
        )

    def start_page_review(self, **kwargs):
        self.start_page_review_called = True
        return SimpleNamespace(pk=13)


class DataCapturePageStateVerificationReopenTests(SimpleTestCase):
    def test_correction_required_page_state_can_be_verified_again_after_reopen(self):
        repository = _CorrectionRequiredVerificationRepository()
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_NoBlockingQueries(),
        )
        service._required_field_template_ids = lambda **kwargs: (1,)

        with patch(
            "apps.datacapture.application.services.page_state_verification_final_data."
            "CrfContextAdapter.list_template_fields_with_ui_config",
            return_value=[{"id": 1, "field_key": "field_1"}],
        ):
            all_verified, page_status, blockers = service.merge_checked_field_template_ids(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                checked_field_template_ids=[1],
                actor_user_id=1,
            )

        self.assertIs(all_verified, True)
        self.assertEqual(page_status, DataCapturePageState.VERIFIED)
        self.assertEqual(blockers, [])
        self.assertIs(repository.start_page_review_called, True)
        self.assertIs(repository.verify_page_state_if_ready_called, True)

    def test_verify_rejects_page_states_outside_reviewable_statuses(self):
        for status in (
            "",
            "none",
            "null",
            DataCapturePageState.NOT_STARTED,
            "not_start",
            DataCapturePageState.IN_PROGRESS,
            DataCapturePageState.VERIFIED,
            DataCapturePageState.LOCKED,
            DataCapturePageState.FINALIZED,
        ):
            repository = _NotReviewableVerificationRepository(status=status)
            service = DataCapturePageStateVerificationFinalDataService(
                repository=repository,
                reconcile_read_service=_NoBlockingQueries(),
            )

            with self.subTest(status=status):
                with self.assertRaises(DataCapturePageVerifyStateError):
                    service.merge_checked_field_template_ids(
                        subject_id=41,
                        visit_id=51,
                        crf_template_id=31,
                        checked_field_template_ids=[1],
                        actor_user_id=1,
                    )

                self.assertIs(repository.start_page_review_called, False)

    def test_reopen_requires_reason_text(self):
        service = DataCapturePageStateVerificationFinalDataService(
            repository=_VerifiedReopenRepository(),
            reconcile_read_service=_NoBlockingQueries(),
        )

        with self.assertRaises(DataCapturePageReopenReasonRequiredError):
            service.reopen_verified_page_state(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                reason_text=" ",
                actor_user_id=1,
            )

    def test_reopen_passes_normalized_reason_to_repository(self):
        repository = _VerifiedReopenRepository()
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_NoBlockingQueries(),
        )

        page_status = service.reopen_verified_page_state(
            subject_id=41,
            visit_id=51,
            crf_template_id=31,
            reason_text="  Need correction after review  ",
            actor_user_id=1,
        )

        self.assertEqual(page_status, DataCapturePageState.CORRECTION_REQUIRED)
        self.assertEqual(
            repository.reopen_kwargs,
            {
                "page_state_id": 12,
                "reason_text": "Need correction after review",
                "actor_user_id": 1,
            },
        )

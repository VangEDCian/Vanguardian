from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.choices import DataCaptureFieldReviewStatusChoices
from apps.datacapture.application.exceptions import (
    DataCapturePageFinalizeStateError,
    DataCapturePageLockStateError,
    DataCapturePageReopenReasonRequiredError,
    DataCapturePageVerifyStateError,
    DataCaptureValidationError,
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
    def has_open_query_for_page_field(self, **kwargs):
        return False

    def has_open_validation_issue_for_page_field(self, **kwargs):
        return False

    def has_active_blocking_query_for_page_field(self, **kwargs):
        return False

    def has_active_blocking_query_for_page(self, **kwargs):
        return False


class _BlockingFieldQueries:
    def has_open_query_for_page_field(self, **kwargs):
        return True

    def has_open_validation_issue_for_page_field(self, **kwargs):
        return False

    def has_active_blocking_query_for_page_field(self, **kwargs):
        return True

    def has_active_blocking_query_for_page(self, **kwargs):
        return True


class _BlockingValidationIssues(_NoBlockingQueries):
    def has_open_validation_issue_for_page_field(self, **kwargs):
        return True


class _CorrectionRequiredVerificationRepository:
    def __init__(self):
        self.status = DataCapturePageState.CORRECTION_REQUIRED
        self.start_page_review_called = False
        self.verify_page_state_if_ready_called = False
        self.all_visit_forms_verified = False
        self.verified_field_template_ids = set()
        self.unverified_reviews = []

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

    def list_verified_field_template_ids(self, **kwargs):
        return set(self.verified_field_template_ids)

    def unverify_field_review(self, **kwargs):
        self.unverified_reviews.append(kwargs)
        return True

    def find_page_verification_field_review_blockers(self, **kwargs):
        if self.unverified_reviews:
            return [
                f"field_review_not_ready:{review['field_template_id']}"
                for review in self.unverified_reviews
            ]
        return []

    def verify_page_state_if_ready(self, **kwargs):
        self.verify_page_state_if_ready_called = True
        self.status = DataCapturePageState.VERIFIED
        return DataCapturePageState.VERIFIED

    def are_all_visit_forms_verified(self, **kwargs):
        return self.all_visit_forms_verified


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


class _PageLifecycleRepository:
    def __init__(self, *, status):
        self.status = status
        self.update_calls = []

    def get_page_state(self, **kwargs):
        return DataCapturePageStateSnapshot(
            id=12,
            status=self.status,
            final_data='{"field_1": "final"}',
            data_version=3,
            current_entry_id=21,
            crf_template_id=31,
            subject_id=41,
            visit_id=51,
            study_id=61,
            study_version="1",
            event_definition_id=71,
        )

    def update_page_state_final_data_and_status(self, **kwargs):
        self.update_calls.append(kwargs)
        self.status = kwargs["status"]


class _GovernanceLockAdapter:
    def __init__(self):
        self.lock_calls = []

    def lock_page_scope(self, **kwargs):
        self.lock_calls.append(kwargs)
        return 501


class _SubjectEventLifecycleAdapter:
    def __init__(self):
        self.completed_event_instances = []
        self.in_progress_event_instances = []
        self.verified_event_instances = []

    def complete_event_instance(self, **kwargs):
        self.completed_event_instances.append(kwargs)
        return True

    def mark_event_instance_in_progress(self, **kwargs):
        self.in_progress_event_instances.append(kwargs)
        return True

    def verify_event_instance(self, **kwargs):
        self.verified_event_instances.append(kwargs)
        return True


class _EventTransitionService:
    def __init__(self):
        self.commands = []

    def execute(self, command):
        self.commands.append(command)


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
            all_verified, page_status, blockers, unverified_ids = service.merge_checked_field_template_ids(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                checked_field_template_ids=[1],
                actor_user_id=1,
            )

        self.assertIs(all_verified, True)
        self.assertEqual(page_status, DataCapturePageState.VERIFIED)
        self.assertEqual(blockers, [])
        self.assertEqual(unverified_ids, [])
        self.assertIs(repository.start_page_review_called, True)
        self.assertIs(repository.verify_page_state_if_ready_called, True)

    def test_verify_marks_visit_verified_when_all_visit_forms_are_verified(self):
        repository = _CorrectionRequiredVerificationRepository()
        repository.all_visit_forms_verified = True
        subject_event_lifecycle_adapter = _SubjectEventLifecycleAdapter()
        event_transition_service = _EventTransitionService()
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_NoBlockingQueries(),
            subject_event_lifecycle_adapter=subject_event_lifecycle_adapter,
            event_transition_service=event_transition_service,
        )
        service._required_field_template_ids = lambda **kwargs: (1,)

        with patch(
            "apps.datacapture.application.services.page_state_verification_final_data."
            "CrfContextAdapter.list_template_fields_with_ui_config",
            return_value=[{"id": 1, "field_key": "field_1"}],
        ):
            service.merge_checked_field_template_ids(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                checked_field_template_ids=[1],
                actor_user_id=1,
            )

        self.assertEqual(
            subject_event_lifecycle_adapter.verified_event_instances,
            [
                {
                    "event_instance_id": 51,
                    "actor_user_id": 1,
                }
            ],
        )
        self.assertEqual(event_transition_service.commands[0].page_state_id, 11)
        self.assertEqual(event_transition_service.commands[0].actor_user_id, 1)
        self.assertEqual(
            event_transition_service.commands[0].trigger_source,
            "datacapture_page_state_verified",
        )

    def test_unchecked_verified_field_becomes_stale_with_reason_text(self):
        repository = _CorrectionRequiredVerificationRepository()
        repository.verified_field_template_ids = {1}
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
            all_verified, page_status, blockers, unverified_ids = service.merge_checked_field_template_ids(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                checked_field_template_ids=[],
                unverify_reason_text="Revert verification",
                actor_user_id=1,
            )

        self.assertIs(all_verified, False)
        self.assertEqual(page_status, DataCapturePageState.UNDER_REVIEW)
        self.assertEqual(unverified_ids, [1])
        self.assertEqual(blockers, ["field_review_not_ready:1"])
        self.assertEqual(
            repository.unverified_reviews[0]["status"],
            DataCaptureFieldReviewStatusChoices.STALE,
        )
        self.assertEqual(repository.unverified_reviews[0]["reason_text"], "Revert verification")

    def test_unchecked_verified_field_requires_reason_text(self):
        repository = _CorrectionRequiredVerificationRepository()
        repository.verified_field_template_ids = {1}
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
            with self.assertRaisesMessage(
                DataCaptureValidationError,
                "Reason for revert verification is required.",
            ):
                service.merge_checked_field_template_ids(
                    subject_id=41,
                    visit_id=51,
                    crf_template_id=31,
                    checked_field_template_ids=[],
                    unverify_reason_text=" ",
                    actor_user_id=1,
                )

        self.assertEqual(repository.unverified_reviews, [])

    def test_verify_rejects_field_with_open_validation_issue(self):
        repository = _CorrectionRequiredVerificationRepository()
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_BlockingValidationIssues(),
        )

        with self.assertRaisesMessage(
            DataCaptureValidationError,
            "yêu cầu xử lý Validation Issues trước khi verify",
        ):
            service.merge_checked_field_template_ids(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                checked_field_template_ids=[1],
                actor_user_id=1,
            )

        self.assertIs(repository.start_page_review_called, False)

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

    def test_verify_rejects_checked_field_with_open_query_before_starting_review(self):
        repository = _CorrectionRequiredVerificationRepository()
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_BlockingFieldQueries(),
        )

        with self.assertRaisesMessage(
            DataCaptureValidationError,
            "yêu cầu đóng Query trước khi verify",
        ):
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
        subject_event_lifecycle_adapter = _SubjectEventLifecycleAdapter()
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_NoBlockingQueries(),
            subject_event_lifecycle_adapter=subject_event_lifecycle_adapter,
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
        self.assertEqual(
            subject_event_lifecycle_adapter.in_progress_event_instances,
            [
                {
                    "event_instance_id": 51,
                    "actor_user_id": 1,
                }
            ],
        )

    def test_finalize_page_data_requires_verified_state(self):
        service = DataCapturePageStateVerificationFinalDataService(
            repository=_PageLifecycleRepository(status=DataCapturePageState.SUBMITTED),
            reconcile_read_service=_NoBlockingQueries(),
        )

        with self.assertRaises(DataCapturePageFinalizeStateError):
            service.finalize_page_data(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                actor_user_id=1,
            )

    def test_finalize_page_data_sets_finalized_status_and_event_source(self):
        repository = _PageLifecycleRepository(status=DataCapturePageState.VERIFIED)
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_NoBlockingQueries(),
        )

        page_status = service.finalize_page_data(
            subject_id=41,
            visit_id=51,
            crf_template_id=31,
            actor_user_id=1,
        )

        self.assertEqual(page_status, DataCapturePageState.FINALIZED)
        self.assertEqual(
            repository.update_calls,
            [
                {
                    "subject_id": 41,
                    "visit_id": 51,
                    "crf_template_id": 31,
                    "final_data": '{"field_1": "final"}',
                    "status": DataCapturePageState.FINALIZED,
                    "actor_user_id": 1,
                    "trigger_source": "PageDataFinalized",
                }
            ],
        )

    def test_lock_page_requires_finalized_state(self):
        service = DataCapturePageStateVerificationFinalDataService(
            repository=_PageLifecycleRepository(status=DataCapturePageState.VERIFIED),
            reconcile_read_service=_NoBlockingQueries(),
            governance_lock_adapter=_GovernanceLockAdapter(),
        )

        with self.assertRaises(DataCapturePageLockStateError):
            service.lock_page(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                actor_user_id=1,
            )

    def test_lock_page_sets_locked_status_and_creates_governance_lock(self):
        repository = _PageLifecycleRepository(status=DataCapturePageState.FINALIZED)
        governance_lock_adapter = _GovernanceLockAdapter()
        service = DataCapturePageStateVerificationFinalDataService(
            repository=repository,
            reconcile_read_service=_NoBlockingQueries(),
            governance_lock_adapter=governance_lock_adapter,
        )

        page_status = service.lock_page(
            subject_id=41,
            visit_id=51,
            crf_template_id=31,
            actor_user_id=1,
        )

        self.assertEqual(page_status, DataCapturePageState.LOCKED)
        self.assertEqual(
            repository.update_calls,
            [
                {
                    "subject_id": 41,
                    "visit_id": 51,
                    "crf_template_id": 31,
                    "final_data": '{"field_1": "final"}',
                    "status": DataCapturePageState.LOCKED,
                    "actor_user_id": 1,
                    "trigger_source": "PageLocked",
                }
            ],
        )
        self.assertEqual(
            governance_lock_adapter.lock_calls,
            [
                {
                    "subject_id": 41,
                    "visit_id": 51,
                    "crf_template_id": 31,
                    "page_state_id": 12,
                    "actor_user_id": 1,
                    "reason": "Lock Page",
                }
            ],
        )

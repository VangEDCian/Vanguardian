from types import SimpleNamespace

from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from apps.core.choices import DataCapturePageEntryStatusChoices, DataCapturePageStateStatusChoices
from apps.datacapture.application.commands import SavePageCommand, SubmitPageCommand
from apps.datacapture.application.services.save_submit_page import DataCaptureSaveSubmitPageService
from apps.datacapture.infrastructure.models.capture import (
    DataCapturePageEntrySnapshot,
    DataCapturePageStateSnapshot,
)


class _NoGovernanceLock:
    def is_capture_locked_for_scope(self, **kwargs):
        return False


class _SubmitReasonRepository:
    def __init__(self, *, page_status):
        self.page_state = DataCapturePageStateSnapshot(
            id=11,
            status=page_status,
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
        self.latest = DataCapturePageEntrySnapshot(
            id=21,
            page_state_id=11,
            parent_entry_id=None,
            entry_no=1,
            entry_kind="initial",
            entry_version="1.0",
            status=DataCapturePageEntryStatusChoices.SUBMITTED,
            data='{"field_1": "old"}',
            crf_template_id=31,
            subject_id=41,
            visit_id=51,
        )
        self.list_changed_verified_field_keys_called = False

    def get_page_state_by_scope(self, **kwargs):
        return self.page_state

    def get_current_entry(self, **kwargs):
        return self.latest

    def has_other_submitted_entry(self, **kwargs):
        return False

    def get_latest_submitted_entry(self, **kwargs):
        return self.latest

    def list_changed_verified_field_keys(self, **kwargs):
        self.list_changed_verified_field_keys_called = True
        return ["field_1"]

    def upsert_page_state_for_data_entry(self, **kwargs):
        return SimpleNamespace(pk=self.page_state.id, data_version=self.page_state.data_version)

    def execute_submit_plan(self, **kwargs):
        return SimpleNamespace(pk=22)

    def list_form_field_validation_rules(self, **kwargs):
        return {}

    def submit_page_state_with_entry(self, **kwargs):
        return SimpleNamespace(pk=self.page_state.id, status=kwargs["target_status"], data_version=4)

    def mark_verified_field_reviews_stale_with_reasons(self, **kwargs):
        return 0

    def mark_field_reviews_stale_for_changed_field_keys(self, **kwargs):
        return 0


def _service(repository):
    return DataCaptureSaveSubmitPageService(
        repository=repository,
        governance_lock_read_repository=_NoGovernanceLock(),
    )


def _submit_without_transaction(service, command):
    return DataCaptureSaveSubmitPageService.submit.__wrapped__(service, command)


def _save_without_transaction(service, command):
    return DataCaptureSaveSubmitPageService.save.__wrapped__(service, command)


class DataCaptureSubmitReasonConditionTests(SimpleTestCase):
    def test_submit_blocks_page_state_lock_statuses_before_change_reason_check(self):
        for status in (
            DataCapturePageStateStatusChoices.VERIFIED,
            DataCapturePageStateStatusChoices.LOCKED,
            DataCapturePageStateStatusChoices.FINALIZED,
        ):
            repository = _SubmitReasonRepository(page_status=status)

            with self.subTest(status=status):
                with self.assertRaisesMessage(PermissionDenied, "Page is not editable"):
                    _submit_without_transaction(
                        _service(repository),
                        SubmitPageCommand(
                            subject_id=41,
                            visit_id=51,
                            crf_template_id=31,
                            data='{"field_1": "new"}',
                            actor_user_id=1,
                        ),
                    )

                self.assertIs(repository.list_changed_verified_field_keys_called, False)

    def test_save_blocks_page_state_lock_statuses(self):
        for status in (
            DataCapturePageStateStatusChoices.VERIFIED,
            DataCapturePageStateStatusChoices.LOCKED,
            DataCapturePageStateStatusChoices.FINALIZED,
        ):
            repository = _SubmitReasonRepository(page_status=status)

            with self.subTest(status=status):
                with self.assertRaisesMessage(PermissionDenied, "Page is not editable"):
                    _save_without_transaction(
                        _service(repository),
                        SavePageCommand(
                            subject_id=41,
                            visit_id=51,
                            crf_template_id=31,
                            data='{"field_1": "new"}',
                            actor_user_id=1,
                        ),
                    )

    def test_submit_does_not_require_change_reason_when_page_state_is_not_locked(self):
        repository = _SubmitReasonRepository(page_status=DataCapturePageStateStatusChoices.SUBMITTED)

        result = _submit_without_transaction(
            _service(repository),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"field_1": "new"}',
                actor_user_id=1,
            ),
        )

        self.assertEqual(result.entry_id, 22)
        self.assertIs(repository.list_changed_verified_field_keys_called, False)

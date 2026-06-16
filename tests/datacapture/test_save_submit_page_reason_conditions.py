from types import SimpleNamespace

from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from apps.core.choices import DataCapturePageEntryStatusChoices, DataCapturePageStateStatusChoices
from apps.datacapture.application.commands import SavePageCommand, SubmitPageCommand
from apps.datacapture.application.exceptions import DataCaptureChangeReasonRequiredError
from apps.datacapture.application.services.save_submit_page import DataCaptureSaveSubmitPageService
from apps.datacapture.infrastructure.models.capture import (
    DataCapturePageEntrySnapshot,
    DataCapturePageStateSnapshot,
)
from apps.datacapture.infrastructure.repositories.page_capture import DjangoDataCapturePageRepository


class _NoGovernanceLock:
    def is_capture_locked_for_scope(self, **kwargs):
        return False


class _SubjectEventLifecycleAdapter:
    def __init__(self):
        self.completed_event_instances = []

    def complete_event_instance(self, **kwargs):
        self.completed_event_instances.append(kwargs)
        return True


class _ReconcileDataQueryWriteService:
    def __init__(self):
        self.update_value_thread_calls = []
        self.validation_failure_record_calls = []

    def add_update_value_threads_for_changed_fields(self, **kwargs):
        self.update_value_thread_calls.append(kwargs)
        return 1

    def create_validation_failure_records(self, **kwargs):
        self.validation_failure_record_calls.append(kwargs)
        return {"soft_issue_count": 1, "query_count": 0}


class _SubmitReasonRepository:
    def __init__(
        self,
        *,
        page_status,
        all_visit_forms_submitted=False,
        changed_verified_field_keys=(),
        validation_rules_by_field_key=None,
    ):
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
        self.all_visit_forms_submitted = all_visit_forms_submitted
        self.changed_verified_field_keys = list(changed_verified_field_keys)
        self.validation_rules_by_field_key = validation_rules_by_field_key or {}
        self.submit_page_state_calls = []

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
        return list(self.changed_verified_field_keys)

    def upsert_page_state_for_data_entry(self, **kwargs):
        return SimpleNamespace(pk=self.page_state.id, data_version=self.page_state.data_version)

    def execute_submit_plan(self, **kwargs):
        return SimpleNamespace(pk=22)

    def list_form_field_validation_rules(self, **kwargs):
        return self.validation_rules_by_field_key

    def submit_page_state_with_entry(self, **kwargs):
        self.submit_page_state_calls.append(kwargs)
        return SimpleNamespace(pk=self.page_state.id, status=kwargs["target_status"], data_version=4)

    def are_all_visit_forms_submitted(self, **kwargs):
        return self.all_visit_forms_submitted

    def mark_verified_field_reviews_stale_with_reasons(self, **kwargs):
        return 0

    def mark_field_reviews_stale_for_changed_field_keys(self, **kwargs):
        return 0


def _service(repository, subject_event_lifecycle_adapter=None, reconcile_data_query_write_service=None):
    return DataCaptureSaveSubmitPageService(
        repository=repository,
        governance_lock_read_repository=_NoGovernanceLock(),
        subject_event_lifecycle_adapter=subject_event_lifecycle_adapter or _SubjectEventLifecycleAdapter(),
        reconcile_data_query_write_service=reconcile_data_query_write_service or _ReconcileDataQueryWriteService(),
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

    def test_submit_requires_change_reason_when_changed_field_is_verified(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            changed_verified_field_keys=["field_1"],
        )

        with self.assertRaises(DataCaptureChangeReasonRequiredError):
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

        self.assertIs(repository.list_changed_verified_field_keys_called, True)

    def test_submit_accepts_change_reason_for_verified_repeat_field(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            changed_verified_field_keys=["field_1__repeat_2"],
        )
        service = _service(repository)
        service.page_entry_state_events = SimpleNamespace(dispatch=lambda *args, **kwargs: None)

        result = _submit_without_transaction(
            service,
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"field_1": "old", "field_1__repeat_2": "new"}',
                change_reasons=(
                    SimpleNamespace(
                        field_key="field_1__repeat_2",
                        field_label="Field 1",
                        reason="Removed stale repeat row",
                    ),
                ),
                actor_user_id=1,
            ),
        )

        self.assertEqual(result.entry_id, 22)
        self.assertIs(repository.list_changed_verified_field_keys_called, True)

    def test_submit_does_not_require_change_reason_when_changed_field_is_not_verified(self):
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
        self.assertIs(repository.list_changed_verified_field_keys_called, True)

    def test_submit_completes_visit_when_all_visit_forms_are_submitted(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            all_visit_forms_submitted=True,
        )
        subject_event_lifecycle_adapter = _SubjectEventLifecycleAdapter()

        _submit_without_transaction(
            _service(repository, subject_event_lifecycle_adapter=subject_event_lifecycle_adapter),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"field_1": "new"}',
                actor_user_id=1,
            ),
        )

        self.assertEqual(
            subject_event_lifecycle_adapter.completed_event_instances,
            [
                {
                    "event_instance_id": 51,
                    "actor_user_id": 1,
                }
            ],
        )

    def test_submit_adds_update_value_threads_for_changed_fields_with_open_queries(self):
        repository = _SubmitReasonRepository(page_status=DataCapturePageStateStatusChoices.SUBMITTED)
        reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

        _submit_without_transaction(
            _service(
                repository,
                reconcile_data_query_write_service=reconcile_data_query_write_service,
            ),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"field_1": "new"}',
                actor_user_id=1,
            ),
        )

        self.assertEqual(
            reconcile_data_query_write_service.update_value_thread_calls,
            [
                {
                    "page_state_id": 11,
                    "crf_template_id": 31,
                    "values_by_field_key": {"field_1": "new"},
                    "actor_user_id": 1,
                },
            ],
        )

    def test_submit_creates_soft_validation_issue_records_when_field_validation_fails(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "field_1": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "warning",
                        "expression": "$val == 'new'",
                        "message": "Value should match expected.",
                    },
                )
            },
        )
        reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

        result = _submit_without_transaction(
            _service(repository, reconcile_data_query_write_service=reconcile_data_query_write_service),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"field_1": "new"}',
                actor_user_id=1,
            ),
        )

        self.assertEqual(result.page_status, DataCapturePageStateStatusChoices.SUBMITTED)
        self.assertEqual(
            repository.submit_page_state_calls[-1]["target_status"],
            DataCapturePageStateStatusChoices.SUBMITTED,
        )
        self.assertEqual(
            reconcile_data_query_write_service.validation_failure_record_calls,
            [
                {
                    "page_state_id": 11,
                    "failures": [
                        {
                            "rule_id": 101,
                            "field_template_id": 1,
                            "field_key": "field_1",
                            "mode": "SOFT",
                            "severity": "warning",
                            "message": "Value should match expected.",
                            "failed_value": "new",
                        }
                    ],
                    "actor_user_id": 1,
                }
            ],
        )

    def test_submit_stops_checking_field_validation_rules_after_first_failure(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "field_1": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "warning",
                        "expression": "$val == 'new'",
                        "message": "First failure.",
                    },
                    {
                        "id": 102,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "warning",
                        "expression": "$val == 'new'",
                        "message": "Second failure.",
                    },
                )
            },
        )
        reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

        _submit_without_transaction(
            _service(repository, reconcile_data_query_write_service=reconcile_data_query_write_service),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"field_1": "new"}',
                actor_user_id=1,
            ),
        )

        failures = reconcile_data_query_write_service.validation_failure_record_calls[0]["failures"]
        self.assertEqual([failure["rule_id"] for failure in failures], [101])

    def test_submit_checks_later_field_validation_rules_after_earlier_rules_pass(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "field_1": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "warning",
                        "expression": "$val == 'other'",
                        "message": "First failure.",
                    },
                    {
                        "id": 102,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "warning",
                        "expression": "$val == 'new'",
                        "message": "Second failure.",
                    },
                )
            },
        )
        reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

        _submit_without_transaction(
            _service(repository, reconcile_data_query_write_service=reconcile_data_query_write_service),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"field_1": "new"}',
                actor_user_id=1,
            ),
        )

        failures = reconcile_data_query_write_service.validation_failure_record_calls[0]["failures"]
        self.assertEqual([failure["rule_id"] for failure in failures], [102])

    def test_custom_expression_supports_num_function_for_error_expression(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "AGE": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "warning",
                        "expression": "$val != '' and 18 > num($val)",
                        "message": "Age must be at least 18.",
                    },
                )
            },
        )
        reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

        _submit_without_transaction(
            _service(repository, reconcile_data_query_write_service=reconcile_data_query_write_service),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"AGE": "17"}',
                actor_user_id=1,
            ),
        )

        self.assertEqual(len(reconcile_data_query_write_service.validation_failure_record_calls), 1)

    def test_submit_sets_page_status_submitted_when_field_validation_passes(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "field_1": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "warning",
                        "expression": "$val != 'new'",
                        "message": "Value should match new.",
                    },
                )
            },
        )

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

        self.assertEqual(result.page_status, DataCapturePageStateStatusChoices.SUBMITTED)
        self.assertEqual(
            repository.submit_page_state_calls[-1]["target_status"],
            DataCapturePageStateStatusChoices.SUBMITTED,
        )

    def test_custom_expression_supports_today_token(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "ICF_DATE": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "QUERY",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "MAJOR",
                        "expression": "$val > $today",
                        "message": "ICF date must not be in the future.",
                    },
                )
            },
        )
        reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

        _submit_without_transaction(
            _service(repository, reconcile_data_query_write_service=reconcile_data_query_write_service),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"ICF_DATE": "9999-01-01"}',
                actor_user_id=1,
            ),
        )

        self.assertEqual(len(reconcile_data_query_write_service.validation_failure_record_calls), 1)

    def test_custom_expression_supports_other_field_token(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "ICF_DATE": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "QUERY",
                        "rule_type": "CUSTOM_EXPRESSION",
                        "severity": "MAJOR",
                        "expression": "$val > $field.SCREENING_VISIT_DATE",
                        "message": "ICF date must not be after screening visit date.",
                    },
                )
            },
        )
        reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

        _submit_without_transaction(
            _service(repository, reconcile_data_query_write_service=reconcile_data_query_write_service),
            SubmitPageCommand(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                data='{"ICF_DATE": "2026-01-03", "SCREENING_VISIT_DATE": "2026-01-02"}',
                actor_user_id=1,
            ),
        )

        self.assertEqual(len(reconcile_data_query_write_service.validation_failure_record_calls), 1)

    def test_submit_creates_soft_validation_issue_records_when_required_field_is_missing_or_empty(self):
        for payload in ("{}", '{"field_1": ""}'):
            with self.subTest(payload=payload):
                repository = _SubmitReasonRepository(
                    page_status=DataCapturePageStateStatusChoices.SUBMITTED,
                    validation_rules_by_field_key={
                        "field_1": (
                            {
                                "id": 101,
                                "field_template_id": 1,
                                "mode": "SOFT",
                                "rule_type": "REQUIRED",
                                "severity": "warning",
                                "expression": "",
                                "message": "Field is required.",
                            },
                        )
                    },
                )
                reconcile_data_query_write_service = _ReconcileDataQueryWriteService()

                result = _submit_without_transaction(
                    _service(repository, reconcile_data_query_write_service=reconcile_data_query_write_service),
                    SubmitPageCommand(
                        subject_id=41,
                        visit_id=51,
                        crf_template_id=31,
                        data=payload,
                        actor_user_id=1,
                    ),
                )

                self.assertEqual(result.page_status, DataCapturePageStateStatusChoices.SUBMITTED)
                self.assertEqual(
                    repository.submit_page_state_calls[-1]["target_status"],
                    DataCapturePageStateStatusChoices.SUBMITTED,
                )
                self.assertEqual(len(reconcile_data_query_write_service.validation_failure_record_calls), 1)

    def test_submit_sets_page_status_submitted_when_required_field_has_value(self):
        repository = _SubmitReasonRepository(
            page_status=DataCapturePageStateStatusChoices.SUBMITTED,
            validation_rules_by_field_key={
                "field_1": (
                    {
                        "id": 101,
                        "field_template_id": 1,
                        "mode": "SOFT",
                        "rule_type": "REQUIRED",
                        "severity": "warning",
                        "expression": "",
                        "message": "Field is required.",
                    },
                )
            },
        )

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

        self.assertEqual(result.page_status, DataCapturePageStateStatusChoices.SUBMITTED)
        self.assertEqual(
            repository.submit_page_state_calls[-1]["target_status"],
            DataCapturePageStateStatusChoices.SUBMITTED,
        )


class DataCaptureLookupPersistenceTests(SimpleTestCase):
    def test_select2_lookup_key_reads_options_from_ui_config_translation(self):
        repository = DjangoDataCapturePageRepository()
        field = SimpleNamespace(
            ui_config=SimpleNamespace(
                control_type="SELECT2",
                translations=SimpleNamespace(
                    all=lambda: [
                        SimpleNamespace(
                            language_code="en",
                            options='{"source": "lookup", "lookup": "hospital"}',
                        )
                    ]
                ),
            )
        )

        self.assertEqual(repository._select2_lookup_key_for_field(field), "hospital")

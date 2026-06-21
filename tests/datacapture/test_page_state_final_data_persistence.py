from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.choices import DataCapturePageStateStatusChoices
from apps.datacapture.infrastructure.repositories.page_capture import DjangoDataCapturePageRepository


class _FinalDataRepository(DjangoDataCapturePageRepository):
    def __init__(self):
        self.build_calls = []
        self.transition_calls = []

    @staticmethod
    def _now():
        return "now"

    def _build_page_state_final_data_from_field_reviews(self, **kwargs) -> str:
        self.build_calls.append(kwargs)
        return '{"field_1": "final"}'

    def _record_page_state_transition(self, **kwargs) -> None:
        self.transition_calls.append(kwargs)


class DataCapturePageStateFinalDataPersistenceTests(SimpleTestCase):
    def test_final_data_is_empty_for_non_stable_statuses(self):
        repository = _FinalDataRepository()

        result = repository._page_state_final_data_for_status(
            status=DataCapturePageStateStatusChoices.SUBMITTED,
            page_state_id=11,
            data_version=3,
        )

        self.assertEqual(result, repository.EMPTY_PAGE_STATE_FINAL_DATA)
        self.assertEqual(repository.build_calls, [])

    def test_final_data_is_built_for_verified_locked_and_finalized_statuses(self):
        repository = _FinalDataRepository()

        results = [
            repository._page_state_final_data_for_status(
                status=status,
                page_state_id=11,
                data_version=3,
            )
            for status in (
                DataCapturePageStateStatusChoices.VERIFIED,
                DataCapturePageStateStatusChoices.LOCKED,
                DataCapturePageStateStatusChoices.FINALIZED,
            )
        ]

        self.assertEqual(results, ['{"field_1": "final"}'] * 3)
        self.assertEqual(
            repository.build_calls,
            [
                {
                    "status": DataCapturePageStateStatusChoices.VERIFIED,
                    "page_state_id": 11,
                    "data_version": 3,
                    "review_type": "data_review",
                },
                {
                    "status": DataCapturePageStateStatusChoices.LOCKED,
                    "page_state_id": 11,
                    "data_version": 3,
                    "review_type": "data_review",
                },
                {
                    "status": DataCapturePageStateStatusChoices.FINALIZED,
                    "page_state_id": 11,
                    "data_version": 3,
                    "review_type": "data_review",
                }
            ],
        )

    def test_lifecycle_status_update_clears_final_data_when_not_stable(self):
        repository = _FinalDataRepository()

        result = repository._page_state_final_data_for_lifecycle_status(
            status=DataCapturePageStateStatusChoices.SUBMITTED,
            current_final_data='{"field_1": "old"}',
        )

        self.assertEqual(result, repository.EMPTY_PAGE_STATE_FINAL_DATA)

    def test_lifecycle_status_update_preserves_stable_final_data_when_snapshot_context_is_missing(self):
        repository = _FinalDataRepository()

        result = repository._page_state_final_data_for_lifecycle_status(
            status=DataCapturePageStateStatusChoices.VERIFIED,
            current_final_data='{"field_1": "final"}',
        )

        self.assertEqual(result, '{"field_1": "final"}')

    def test_lifecycle_status_update_builds_stable_final_data_with_snapshot_context(self):
        repository = _FinalDataRepository()

        result = repository._page_state_final_data_for_lifecycle_status(
            status=DataCapturePageStateStatusChoices.LOCKED,
            current_final_data='{"field_1": "old"}',
            page_state_id=11,
            data_version=3,
        )

        self.assertEqual(result, '{"field_1": "final"}')
        self.assertEqual(
            repository.build_calls,
            [
                {
                    "status": DataCapturePageStateStatusChoices.LOCKED,
                    "page_state_id": 11,
                    "data_version": 3,
                    "review_type": "data_review",
                }
            ],
        )

    def test_new_non_finalized_page_state_starts_with_empty_final_data(self):
        repository = _FinalDataRepository()
        repository._resolve_event_form_binding_id_for_scope = lambda **kwargs: 77
        repository._resolve_default_page_state_repeat_index_for_scope = lambda **kwargs: 2

        with patch(
            "apps.datacapture.infrastructure.repositories.page_capture.DataCapturePageState.objects"
        ) as page_state_objects:
            page_state_objects.filter.return_value.order_by.return_value.first.return_value = None
            page_state_objects.create.return_value = SimpleNamespace(pk=11, data_version=1)

            repository.upsert_page_state(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                status=DataCapturePageStateStatusChoices.NOT_STARTED,
                actor_user_id=1,
                trigger_source="system",
            )

        page_state_objects.create.assert_called_once()
        self.assertEqual(
            page_state_objects.create.call_args.kwargs["event_form_binding_id"],
            77,
        )
        self.assertEqual(
            page_state_objects.create.call_args.kwargs["repeat_index"],
            2,
        )
        self.assertEqual(
            page_state_objects.create.call_args.kwargs["final_data"],
            repository.EMPTY_PAGE_STATE_FINAL_DATA,
        )

    def test_new_stable_page_state_builds_final_data_after_create(self):
        repository = _FinalDataRepository()
        repository._resolve_event_form_binding_id_for_scope = lambda **kwargs: 88
        repository._resolve_default_page_state_repeat_index_for_scope = lambda **kwargs: 3

        with patch(
            "apps.datacapture.infrastructure.repositories.page_capture.DataCapturePageState.objects"
        ) as page_state_objects:
            page_state_objects.filter.return_value.order_by.return_value.first.return_value = None
            page_state_objects.create.return_value = SimpleNamespace(pk=11, data_version=1, final_data=None)

            page_state = repository.upsert_page_state(
                subject_id=41,
                visit_id=51,
                crf_template_id=31,
                status=DataCapturePageStateStatusChoices.VERIFIED,
                actor_user_id=1,
                trigger_source="system",
            )

        self.assertEqual(page_state.final_data, '{"field_1": "final"}')
        self.assertEqual(
            repository.build_calls,
            [
                {
                    "status": DataCapturePageStateStatusChoices.VERIFIED,
                    "page_state_id": 11,
                    "data_version": 1,
                    "review_type": "data_review",
                }
            ],
        )
        self.assertEqual(
            page_state_objects.create.call_args.kwargs["event_form_binding_id"],
            88,
        )
        self.assertEqual(
            page_state_objects.create.call_args.kwargs["repeat_index"],
            3,
        )
        page_state_objects.filter.return_value.update.assert_called_once_with(final_data='{"field_1": "final"}')

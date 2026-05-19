from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.choices import (
    DataCaptureFieldReviewStatusChoices,
    DataCaptureFieldReviewTypeChoices,
    DataCapturePageStateStatusChoices,
)
from apps.datacapture.infrastructure.repositories.page_capture import DjangoDataCapturePageRepository


class _ReviewQuery:
    def __init__(self, *, rows=None, first_row=None, values=None):
        self.rows = rows or []
        self.first_row = first_row
        self.values = values or []
        self.updated_with = None

    def only(self, *args):
        return self.rows

    def values_list(self, *args, **kwargs):
        return self.values

    def first(self):
        return self.first_row

    def update(self, **kwargs):
        self.updated_with = kwargs
        return 1


class DataCaptureFieldReviewRepositoryTests(SimpleTestCase):
    def test_ensure_field_reviews_replaces_stale_record(self):
        repository = DjangoDataCapturePageRepository()
        stale_review = SimpleNamespace(
            id=7,
            field_template_id=2,
            deleted=False,
            status=DataCaptureFieldReviewStatusChoices.STALE,
        )
        stale_query = _ReviewQuery(rows=[stale_review])
        mark_deleted_query = _ReviewQuery()
        active_query = _ReviewQuery(values=[])
        field_review_model = MagicMock()
        field_review_model.objects.filter.side_effect = [
            stale_query,
            mark_deleted_query,
            active_query,
        ]

        with patch(
            "apps.datacapture.infrastructure.repositories.page_capture.DataCaptureFieldReview",
            field_review_model,
        ):
            count = repository.ensure_field_reviews_for_page(
                page_state_id=1,
                field_template_ids=(2,),
                data_version=3,
                actor_user_id=4,
            )

        self.assertEqual(count, 1)
        self.assertEqual(mark_deleted_query.updated_with["deleted"], True)
        field_review_model.objects.bulk_create.assert_called_once()

    def test_verify_field_review_replaces_stale_record(self):
        repository = DjangoDataCapturePageRepository()
        stale_review = SimpleNamespace(
            pk=7,
            deleted=False,
            status=DataCaptureFieldReviewStatusChoices.STALE,
            reviewed_at=None,
        )
        new_review = SimpleNamespace(
            pk=8,
            status=DataCaptureFieldReviewStatusChoices.NOT_REVIEWED,
            reviewed_at=None,
        )
        stale_query = _ReviewQuery(first_row=stale_review)
        mark_deleted_query = _ReviewQuery()
        verify_query = _ReviewQuery()
        field_review_model = MagicMock()
        field_review_model.objects.filter.side_effect = [
            stale_query,
            mark_deleted_query,
            verify_query,
        ]
        field_review_model.objects.create.return_value = new_review

        with patch(
            "apps.datacapture.infrastructure.repositories.page_capture.DataCaptureFieldReview",
            field_review_model,
        ):
            repository.verify_field_review(
                page_state_id=1,
                field_template_id=2,
                data_version=3,
                value_snapshot="value",
                actor_user_id=4,
            )

        self.assertEqual(mark_deleted_query.updated_with["deleted"], True)
        field_review_model.objects.create.assert_called_once()
        self.assertEqual(verify_query.updated_with["deleted"], False)
        self.assertEqual(
            verify_query.updated_with["status"],
            DataCaptureFieldReviewStatusChoices.VERIFIED,
        )
        self.assertEqual(verify_query.updated_with["data_version"], 3)
        self.assertEqual(verify_query.updated_with["value_snapshot"], "value")

    def test_reopen_verified_page_state_marks_verified_field_reviews_stale(self):
        repository = DjangoDataCapturePageRepository()
        page_state = SimpleNamespace(
            pk=12,
            status=DataCapturePageStateStatusChoices.VERIFIED,
            refresh_from_db=lambda: None,
        )
        page_lookup_query = _ReviewQuery(first_row=page_state)
        page_update_query = _ReviewQuery()
        field_review_query = _ReviewQuery()
        page_state_model = MagicMock()
        page_state_model.objects.filter.side_effect = [page_lookup_query, page_update_query]
        field_review_model = MagicMock()
        field_review_model.objects.filter.return_value = field_review_query

        with (
            patch(
                "apps.datacapture.infrastructure.repositories.page_capture.DataCapturePageState",
                page_state_model,
            ),
            patch(
                "apps.datacapture.infrastructure.repositories.page_capture.DataCaptureFieldReview",
                field_review_model,
            ),
            patch.object(repository, "_record_page_state_transition"),
        ):
            page_status = repository.reopen_verified_page_state(
                page_state_id=12,
                reason_text="Need correction",
                actor_user_id=4,
            )

        self.assertEqual(page_status, DataCapturePageStateStatusChoices.CORRECTION_REQUIRED.value)
        _, filter_kwargs = field_review_model.objects.filter.call_args
        self.assertEqual(filter_kwargs["page_state_id"], 12)
        self.assertEqual(filter_kwargs["review_type"], DataCaptureFieldReviewTypeChoices.DATA_REVIEW)
        self.assertEqual(filter_kwargs["deleted"], False)
        self.assertEqual(filter_kwargs["status"], DataCaptureFieldReviewStatusChoices.VERIFIED)
        self.assertEqual(field_review_query.updated_with["status"], DataCaptureFieldReviewStatusChoices.STALE)
        self.assertEqual(field_review_query.updated_with["reason_code"], "reopen_form")
        self.assertEqual(field_review_query.updated_with["reason_text"], "Need correction")

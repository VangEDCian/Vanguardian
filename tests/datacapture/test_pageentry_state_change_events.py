from django.test import SimpleTestCase

from apps.datacapture.application.commands import SubmitFieldChangeReason
from apps.datacapture.application.services.pageentry_state_change_events import (
    PageEntryStateChangeEventDispatcher,
    PageEntrySubmittedEventContext,
)
from apps.datacapture.domain.entities import PageEntryStateChangedEvent
from apps.datacapture.domain.status import DataCapturePageEntry
from apps.shared.constants import AuditEventAction, AuditEventObjectType


class _Repository:
    def __init__(self):
        self.stale_with_reasons_calls = []
        self.stale_changed_keys_calls = []

    def mark_verified_field_reviews_stale_with_reasons(self, **kwargs):
        self.stale_with_reasons_calls.append(kwargs)
        return 1

    def mark_field_reviews_stale_for_changed_field_keys(self, **kwargs):
        self.stale_changed_keys_calls.append(kwargs)
        return 1


class _AuditContext:
    def __init__(self):
        self.recorded_events = []

    def record_event(self, **kwargs):
        self.recorded_events.append(kwargs)


class PageEntryStateChangeEventDispatcherTests(SimpleTestCase):
    def test_submitted_event_runs_review_and_audit_handlers(self):
        repository = _Repository()
        audit_context = _AuditContext()
        dispatcher = PageEntryStateChangeEventDispatcher(
            repository=repository,
            audit_context=audit_context,
        )

        dispatcher.dispatch(
            PageEntryStateChangedEvent(
                entry_id=10,
                page_state_id=20,
                subject_id=30,
                visit_id=40,
                crf_template_id=50,
                from_status=DataCapturePageEntry.DRAFT,
                to_status=DataCapturePageEntry.SUBMITTED,
                actor_user_id=60,
            ),
            context=PageEntrySubmittedEventContext(
                page_state_id=20,
                data_version=3,
                changed_field_keys=("field_1", "field_2"),
                reason_required_field_keys=("field_1",),
                reason_map={
                    "field_1": SubmitFieldChangeReason(
                        field_key="field_1",
                        field_label="Field 1",
                        reason="Corrected source document",
                    ),
                },
                baseline_payload={"field_1": "old", "field_2": "same"},
                candidate_payload={"field_1": "new", "field_2": "changed"},
            ),
        )

        self.assertEqual(
            repository.stale_with_reasons_calls,
            [
                {
                    "page_state_id": 20,
                    "crf_template_id": 50,
                    "data_version": 3,
                    "reason_by_field_key": {"field_1": "Corrected source document"},
                    "actor_user_id": 60,
                }
            ],
        )
        self.assertEqual(repository.stale_changed_keys_calls[0]["changed_field_keys"], ["field_1", "field_2"])
        self.assertEqual(audit_context.recorded_events[0]["action"], AuditEventAction.DATACAPTURE_PAGEENTRY_CHANGE_REASONS_SUBMITTED)
        self.assertEqual(audit_context.recorded_events[0]["object_type"], AuditEventObjectType.PAGEENTRY)
        self.assertEqual(audit_context.recorded_events[0]["object_id"], "10")

    def test_non_submitted_handlers_do_not_require_context(self):
        repository = _Repository()
        dispatcher = PageEntryStateChangeEventDispatcher(
            repository=repository,
            audit_context=_AuditContext(),
        )

        dispatcher.dispatch(
            PageEntryStateChangedEvent(
                entry_id=10,
                page_state_id=20,
                subject_id=30,
                visit_id=40,
                crf_template_id=50,
                from_status=None,
                to_status=DataCapturePageEntry.DRAFT,
                actor_user_id=60,
            )
        )

        self.assertEqual(repository.stale_with_reasons_calls, [])
        self.assertEqual(repository.stale_changed_keys_calls, [])

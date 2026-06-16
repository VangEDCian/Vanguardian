from dataclasses import dataclass, field
from typing import Mapping

from apps.audit.public import AuditContextAdapter
from apps.datacapture.application.commands import SubmitFieldChangeReason
from apps.datacapture.domain.entities import PageEntryStateChangedEvent
from apps.datacapture.domain.status import DataCapturePageEntry
from apps.shared.constants import AuditEventAction, AuditEventObjectType


@dataclass(frozen=True)
class PageEntrySubmittedEventContext:
    page_state_id: int
    data_version: int
    changed_field_keys: tuple[str, ...] = ()
    reason_required_field_keys: tuple[str, ...] = ()
    reason_map: Mapping[str, SubmitFieldChangeReason] = field(default_factory=dict)
    baseline_payload: Mapping[str, object] = field(default_factory=dict)
    candidate_payload: Mapping[str, object] = field(default_factory=dict)


def _resolve_canonical_value(payload_map: Mapping[str, object], canonical_key: str):
    if payload_map.get(canonical_key) is None:
        return ""
    return payload_map.get(canonical_key)


def _build_change_reason_audit_payloads(
    *,
    baseline_payload: Mapping[str, object],
    candidate_payload: Mapping[str, object],
    changed_field_keys: tuple[str, ...],
    reason_map: Mapping[str, SubmitFieldChangeReason],
) -> tuple[dict, dict]:
    before_fields: list[dict] = []
    after_fields: list[dict] = []
    for field_key in changed_field_keys:
        reason_item = reason_map[field_key]
        label = reason_item.field_label or field_key
        before_fields.append(
            {
                "field_key": field_key,
                "field_label": label,
                "value": _resolve_canonical_value(baseline_payload, field_key),
            }
        )
        after_fields.append(
            {
                "field_key": field_key,
                "field_label": label,
                "value": _resolve_canonical_value(candidate_payload, field_key),
                "reason": reason_item.reason,
            }
        )
    return (
        {"changed_fields": before_fields},
        {"changed_fields": after_fields},
    )


class PageEntryStateChangeEventDispatcher:
    """Synchronous application event dispatcher for page-entry status changes."""

    def __init__(self, *, repository, audit_context=None):
        self.repository = repository
        self.audit_context = audit_context or AuditContextAdapter()

    def dispatch(self, event: PageEntryStateChangedEvent, *, context=None) -> None:
        handlers = {
            DataCapturePageEntry.DRAFT: self.on_draft,
            DataCapturePageEntry.SUBMITTED: self.on_submitted,
            DataCapturePageEntry.SUPERSEDED: self.on_superseded,
            DataCapturePageEntry.CANCELLED: self.on_cancelled,
        }
        handler = handlers.get(event.to_status)
        if handler is None:
            return
        handler(event, context)

    def on_draft(self, event: PageEntryStateChangedEvent, context=None) -> None:
        return None

    def on_submitted(
        self,
        event: PageEntryStateChangedEvent,
        context: PageEntrySubmittedEventContext | None = None,
    ) -> None:
        if context is None:
            return
        if context.reason_required_field_keys and context.reason_map:
            self.repository.mark_verified_field_reviews_stale_with_reasons(
                page_state_id=context.page_state_id,
                crf_template_id=event.crf_template_id,
                data_version=context.data_version,
                reason_by_field_key={
                    field_key: context.reason_map[field_key].reason
                    for field_key in context.reason_required_field_keys
                    if field_key in context.reason_map and context.reason_map[field_key].reason
                },
                actor_user_id=event.actor_user_id,
            )
        self.repository.mark_field_reviews_stale_for_changed_field_keys(
            page_state_id=context.page_state_id,
            crf_template_id=event.crf_template_id,
            changed_field_keys=list(context.changed_field_keys),
            actor_user_id=event.actor_user_id,
        )
        changed_field_keys_with_reasons = tuple(
            field_key
            for field_key in context.changed_field_keys
            if field_key in context.reason_map and context.reason_map[field_key].reason
        )
        if not changed_field_keys_with_reasons:
            return
        before_data, after_data = _build_change_reason_audit_payloads(
            baseline_payload=context.baseline_payload,
            candidate_payload=context.candidate_payload,
            changed_field_keys=changed_field_keys_with_reasons,
            reason_map=context.reason_map,
        )
        self.audit_context.record_event(
            action=AuditEventAction.DATACAPTURE_PAGEENTRY_CHANGE_REASONS_SUBMITTED,
            object_type=AuditEventObjectType.PAGEENTRY,
            object_id=str(event.entry_id),
            before_data=before_data,
            after_data=after_data,
            actor_user_id=event.actor_user_id,
        )

    def on_superseded(self, event: PageEntryStateChangedEvent, context=None) -> None:
        return None

    def on_cancelled(self, event: PageEntryStateChangedEvent, context=None) -> None:
        return None


__all__ = [
    "PageEntryStateChangeEventDispatcher",
    "PageEntrySubmittedEventContext",
]

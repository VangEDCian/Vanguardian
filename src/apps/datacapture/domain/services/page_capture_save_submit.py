"""Pure domain rules for save-draft and submit-for-review (no Django / ORM)."""

import json

from apps.core.choices import DataCapturePageEntryStatusChoices
from apps.datacapture.domain.exceptions import (
    InvalidPagePayloadError,
    UnsupportedEntryStatusError,
)
from apps.datacapture.infrastructure.models.capture import (
    DataCapturePageEntrySnapshot,
    DataCapturePageStateSnapshot,
    SaveDraftExecutionPlan,
    SubmitExecutionPlan,
)


def assert_page_editable_for_capture(page_state: DataCapturePageStateSnapshot | None) -> None:
    # Business lock is managed by governance tables, not PageState status.
    _ = page_state


def validate_capture_payload(data: str | None) -> None:
    if not (data or "").strip():
        raise InvalidPagePayloadError("Invalid or empty payload")
    try:
        parsed = json.loads(data or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        raise InvalidPagePayloadError("Invalid or empty payload")
    if not isinstance(parsed, dict):
        raise InvalidPagePayloadError("Invalid or empty payload")


def same_capture_payload(previous_data: str | None, incoming_data: str | None) -> bool:
    if (previous_data or "") == (incoming_data or ""):
        return True
    try:
        previous_obj = json.loads(previous_data or "{}")
        incoming_obj = json.loads(incoming_data or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return previous_obj == incoming_obj


def resolve_save_draft_execution_plan(
    *,
    page_state: DataCapturePageStateSnapshot | None,
    latest: DataCapturePageEntrySnapshot | None,
    payload: str,
) -> SaveDraftExecutionPlan:
    assert_page_editable_for_capture(page_state)
    validate_capture_payload(payload)
    if latest is None:
        return SaveDraftExecutionPlan(branch="create_initial")
    if latest.status == DataCapturePageEntryStatusChoices.DRAFT:
        return SaveDraftExecutionPlan(branch="update_draft")
    if latest.status == DataCapturePageEntryStatusChoices.SUBMITTED:
        if same_capture_payload(latest.data, payload):
            noop_status = page_state.status if page_state is not None else DataCapturePageEntryStatusChoices.SUBMITTED
            return SaveDraftExecutionPlan(branch="noop_identical_submitted", noop_page_status=noop_status)
        return SaveDraftExecutionPlan(branch="correction_from_submitted")
    raise UnsupportedEntryStatusError(
        f"Cannot save draft: latest page entry has unexpected status {latest.status!r}",
    )


def build_submit_execution_plan(
    *,
    page_state: DataCapturePageStateSnapshot | None,
    latest: DataCapturePageEntrySnapshot | None,
    has_other_submitted_entry: bool,
    payload: str,
) -> SubmitExecutionPlan:
    assert_page_editable_for_capture(page_state)
    validate_capture_payload(payload)
    if latest is None:
        return SubmitExecutionPlan(action="initial_submitted")
    if latest.status == DataCapturePageEntryStatusChoices.DRAFT:
        return SubmitExecutionPlan(
            action="promote_draft",
            draft_entry_id=latest.id,
            supersede_other_submitted_before_promote=has_other_submitted_entry,
        )
    if latest.status == DataCapturePageEntryStatusChoices.SUBMITTED:
        return SubmitExecutionPlan(
            action="replace_submitted",
            superseded_entry_snapshot=latest,
        )
    raise UnsupportedEntryStatusError(
        f"submit: unsupported latest page entry status {latest.status!r}",
    )

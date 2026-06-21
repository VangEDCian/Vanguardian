import json

from apps.datacapture.application import (
    DeleteDraftPageCommand,
    SavePageCommand,
    SubmitFieldChangeReason,
    SubmitPageCommand,
)


def _normalize_submit_payload(raw_body: str) -> tuple[str, tuple[SubmitFieldChangeReason, ...]]:
    try:
        parsed = json.loads(raw_body or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return raw_body, ()
    if not isinstance(parsed, dict):
        return raw_body, ()

    raw_data = parsed.get("data")
    raw_reasons = parsed.get("change_reasons")
    if isinstance(raw_data, dict):
        data_payload = raw_data
    else:
        data_payload = parsed
        raw_reasons = []

    reasons: list[SubmitFieldChangeReason] = []
    if isinstance(raw_reasons, list):
        for item in raw_reasons:
            if not isinstance(item, dict):
                continue
            field_key = str(item.get("field_key") or "").strip()
            if not field_key:
                continue
            reasons.append(
                SubmitFieldChangeReason(
                    field_key=field_key,
                    field_label=str(item.get("field_label") or "").strip(),
                    reason=str(item.get("reason") or "").strip(),
                )
            )
    return json.dumps(data_payload), tuple(reasons)


def _extract_event_form_binding_id(raw_body: str) -> int | None:
    try:
        parsed = json.loads(raw_body or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    raw_value = parsed.get("event_form_binding_id")
    try:
        return int(raw_value) if raw_value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def save_page_command_from_post(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    raw_body: str,
    actor_user_id: int | None,
) -> SavePageCommand:
    event_form_binding_id = _extract_event_form_binding_id(raw_body)
    normalized_data, _ = _normalize_submit_payload(raw_body)
    return SavePageCommand(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        data=normalized_data,
        event_form_binding_id=event_form_binding_id,
        actor_user_id=actor_user_id,
    )


def submit_page_command_from_post(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    raw_body: str,
    actor_user_id: int | None,
) -> SubmitPageCommand:
    normalized_data, change_reasons = _normalize_submit_payload(raw_body)
    return SubmitPageCommand(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        data=normalized_data,
        event_form_binding_id=_extract_event_form_binding_id(raw_body),
        change_reasons=change_reasons,
        actor_user_id=actor_user_id,
    )


def delete_draft_page_command_from_post(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    raw_body: str = "",
    actor_user_id: int | None,
) -> DeleteDraftPageCommand:
    return DeleteDraftPageCommand(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        event_form_binding_id=_extract_event_form_binding_id(raw_body),
        actor_user_id=actor_user_id,
    )

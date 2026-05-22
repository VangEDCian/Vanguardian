from apps.reconcile.application import (
    ReconcileChangeReasonItem,
    ReconcileDataQueryReadService,
    ReconcileDataQueryWriteService,
)


def create_data_queries_for_page_change_reasons(
    *,
    page_state_id: int,
    crf_template_id: int,
    reasons: list[dict[str, str]],
    actor_user_id: int | None,
) -> int:
    reason_items = [
        ReconcileChangeReasonItem(
            field_key=str(item.get("field_key") or "").strip(),
            field_label=str(item.get("field_label") or "").strip(),
            reason=str(item.get("reason") or "").strip(),
        )
        for item in reasons
        if isinstance(item, dict)
    ]
    return ReconcileDataQueryWriteService().create_change_reason_data_queries(
        page_state_id=page_state_id,
        crf_template_id=crf_template_id,
        reasons=reason_items,
        actor_user_id=actor_user_id,
    )


def open_reconcile_query(
    *,
    page_state_id: int,
    field_template_id: int,
    message_text: str,
    actor_user_id: int | None,
    field_key: str = "",
) -> dict[str, object]:
    return ReconcileDataQueryWriteService().open_query(
        page_state_id=page_state_id,
        field_template_id=field_template_id,
        field_key=field_key,
        message_text=message_text,
        actor_user_id=actor_user_id,
    )


def has_verified_reconcile_query_for_page_field(*, page_state_id: int, field_template_id: int) -> bool:
    return ReconcileDataQueryReadService().has_verified_query_for_page_field(
        page_state_id=page_state_id,
        field_template_id=field_template_id,
    )


def reply_to_reconcile_query(
    *,
    dataquery_id: int,
    page_state_id: int,
    field_template_id: int,
    message_text: str,
    actor_user_id: int | None,
) -> dict[str, object]:
    return ReconcileDataQueryWriteService().reply_to_query(
        dataquery_id=dataquery_id,
        page_state_id=page_state_id,
        field_template_id=field_template_id,
        message_text=message_text,
        actor_user_id=actor_user_id,
    )


def cancel_reconcile_query(
    *,
    dataquery_id: int,
    page_state_id: int,
    field_template_id: int,
    actor_user_id: int | None,
) -> dict[str, object]:
    return ReconcileDataQueryWriteService().cancel_query(
        dataquery_id=dataquery_id,
        page_state_id=page_state_id,
        field_template_id=field_template_id,
        actor_user_id=actor_user_id,
    )


def reply_and_close_reconcile_query(
    *,
    dataquery_id: int,
    page_state_id: int,
    field_template_id: int,
    message_text: str,
    actor_user_id: int | None,
    is_resolved: bool = False,
) -> dict[str, object]:
    return ReconcileDataQueryWriteService().reply_and_close_query(
        dataquery_id=dataquery_id,
        page_state_id=page_state_id,
        field_template_id=field_template_id,
        message_text=message_text,
        actor_user_id=actor_user_id,
        is_resolved=is_resolved,
    )


__all__ = [
    "cancel_reconcile_query",
    "create_data_queries_for_page_change_reasons",
    "has_verified_reconcile_query_for_page_field",
    "open_reconcile_query",
    "reply_and_close_reconcile_query",
    "reply_to_reconcile_query",
]

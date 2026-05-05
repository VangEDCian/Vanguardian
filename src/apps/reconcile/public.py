from apps.reconcile.application import (
    ReconcileChangeReasonItem,
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


__all__ = [
    "create_data_queries_for_page_change_reasons",
]


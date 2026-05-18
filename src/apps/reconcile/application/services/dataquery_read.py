from apps.reconcile.infrastructure.repositories import DjangoReconcileDataQueryReadRepository


class ReconcileDataQueryReadService:
    def __init__(self, repository=None):
        self.repository = repository or DjangoReconcileDataQueryReadRepository()

    def count_open_queries_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, int]:
        return self.repository.count_open_queries_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def has_active_blocking_query_for_page_field(self, *, page_state_id: int, field_template_id: int) -> bool:
        return self.repository.has_active_blocking_query_for_page_field(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
        )

    def has_active_blocking_query_for_page(self, *, page_state_id: int) -> bool:
        return self.repository.has_active_blocking_query_for_page(page_state_id=page_state_id)

    def list_latest_query_messages_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
        limit_per_field: int = 10,
    ) -> dict[int, list[dict[str, object]]]:
        return self.repository.list_latest_query_messages_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
            limit_per_field=limit_per_field,
        )

    def list_latest_active_query_ids_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, int]:
        return self.repository.list_latest_active_query_ids_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def count_query_threads_since_current_user_last_comment(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
        current_user_id: int | None,
    ) -> dict[int, int]:
        return self.repository.count_query_threads_since_current_user_last_comment(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
            current_user_id=current_user_id,
        )


__all__ = ["ReconcileDataQueryReadService"]

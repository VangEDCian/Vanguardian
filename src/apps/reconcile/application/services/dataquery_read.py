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

    def list_open_validation_issues_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, list[dict[str, object]]]:
        return self.repository.list_open_validation_issues_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def list_validation_issue_histories_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, list[dict[str, object]]]:
        return self.repository.list_validation_issue_histories_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def has_open_validation_issue_for_page_field(self, *, page_state_id: int, field_template_id: int) -> bool:
        return self.repository.has_open_validation_issue_for_page_field(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
        )

    def has_open_query_for_page_field(self, *, page_state_id: int, field_template_id: int) -> bool:
        return self.repository.has_open_query_for_page_field(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
        )

    def list_field_template_ids_with_verified_queries(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> set[int]:
        return self.repository.list_field_template_ids_with_verified_queries(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def list_verified_query_keys_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> set[tuple[int, str]]:
        return self.repository.list_verified_query_keys_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def has_verified_query_for_page_field(self, *, page_state_id: int, field_template_id: int) -> bool:
        return self.repository.has_verified_query_for_page_field(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
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

    def list_latest_query_messages_by_dataquery_ids(
        self,
        *,
        dataquery_ids: tuple[int, ...],
        limit_per_query: int = 10,
    ) -> dict[int, list[dict[str, object]]]:
        return self.repository.list_latest_query_messages_by_dataquery_ids(
            dataquery_ids=dataquery_ids,
            limit_per_query=limit_per_query,
        )

    def list_closed_query_histories_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
        limit_per_query: int = 10,
    ) -> dict[int, list[dict[str, object]]]:
        return self.repository.list_closed_query_histories_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
            limit_per_query=limit_per_query,
        )

    def list_closed_query_histories_by_page_state_field_paths(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
        limit_per_query: int = 10,
    ) -> dict[tuple[int, str], list[dict[str, object]]]:
        return self.repository.list_closed_query_histories_by_page_state_field_paths(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
            limit_per_query=limit_per_query,
        )

    def count_open_queries_by_page_state_field_paths(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[tuple[int, str], int]:
        return self.repository.count_open_queries_by_page_state_field_paths(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def list_latest_active_query_contexts_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[tuple[int, str], dict[str, object]]:
        return self.repository.list_latest_active_query_contexts_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
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

    def list_latest_active_query_answered_flags_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, bool]:
        return self.repository.list_latest_active_query_answered_flags_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )

    def list_latest_active_query_participants_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, dict[str, int | None]]:
        return self.repository.list_latest_active_query_participants_by_page_state_and_field_templates(
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

    def count_query_threads_since_current_user_last_comment_by_dataquery_ids(
        self,
        *,
        dataquery_ids: tuple[int, ...],
        current_user_id: int | None,
    ) -> dict[int, int]:
        return self.repository.count_query_threads_since_current_user_last_comment_by_dataquery_ids(
            dataquery_ids=dataquery_ids,
            current_user_id=current_user_id,
        )

    def count_open_queries_assigned_to_user(
        self,
        *,
        page_state_ids: tuple[int, ...],
        user_id: int | None,
    ) -> int:
        return self.repository.count_open_queries_assigned_to_user(
            page_state_ids=page_state_ids,
            user_id=user_id,
        )


__all__ = ["ReconcileDataQueryReadService"]

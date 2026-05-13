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


__all__ = ["ReconcileDataQueryReadService"]

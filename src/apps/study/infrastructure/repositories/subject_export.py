from apps.study.models import EventDefinition, EventFormBinding


class DjangoSubjectExportFieldCatalogRepository:
    def resolve_active_study_version(self, *, study_id: int) -> str | None:
        return (
            EventDefinition.objects.filter(
                study_id=study_id,
                deleted=False,
                is_enabled=True,
            )
            .order_by("-updated_at", "-id")
            .values_list("study_version", flat=True)
            .first()
        )

    def list_enabled_bindings(
        self,
        *,
        study_id: int,
        study_version: str,
    ):
        return (
            EventFormBinding.objects.filter(
                study_id=study_id,
                study_version=study_version,
                deleted=False,
                is_enabled=True,
                event_definition__deleted=False,
                event_definition__is_enabled=True,
                form_definition__deleted=False,
                form_definition__is_active=True,
            )
            .select_related("event_definition", "form_definition")
            .prefetch_related("form_definition__translations")
            .order_by(
                "event_definition__sequence_no",
                "event_definition_id",
                "display_order",
                "id",
            )
        )


__all__ = ["DjangoSubjectExportFieldCatalogRepository"]

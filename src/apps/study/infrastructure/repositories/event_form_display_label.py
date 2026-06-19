from apps.study.models import (
    EventFormBinding,
    EventFormDisplayConfig,
    EventFormDisplayConfigTranslation,
)


class DjangoEventFormDisplayLabelRepository:
    def get_binding(self, *, binding_id: int):
        return (
            EventFormBinding.objects.filter(pk=binding_id, deleted=False)
            .select_related("form_definition", "event_definition")
            .prefetch_related("form_definition__translations", "display_config__translations")
            .first()
        )

    def list_bindings(self, *, study_id: int):
        return (
            EventFormBinding.objects.filter(study_id=study_id, deleted=False, is_enabled=True)
            .select_related("event_definition", "form_definition")
            .prefetch_related("form_definition__translations", "display_config__translations")
            .order_by("event_definition__sequence_no", "display_order", "id")
        )

    def get_active_config(self, *, binding_id: int):
        return EventFormDisplayConfig.objects.filter(
            event_form_binding_id=binding_id,
            deleted=False,
        ).first()

    def create_config(self, **kwargs):
        return EventFormDisplayConfig.objects.create(**kwargs)

    def save_config(self, config, *, update_fields: list[str]):
        config.save(update_fields=update_fields)
        return config

    def upsert_translation(self, *, config, language_code: str, payload: dict):
        return EventFormDisplayConfigTranslation.objects.update_or_create(
            display_config=config,
            language_code=language_code,
            defaults=payload,
        )

    def get_binding_snapshot(self, *, binding_id: int):
        return (
            EventFormBinding.objects.filter(pk=binding_id, deleted=False, is_enabled=True)
            .values(
                "id",
                "study_id",
                "study_version",
                "event_definition_id",
                "form_definition_id",
                "is_repeatable_within_event",
                "display_order",
            )
            .first()
        )

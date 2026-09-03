from apps.crf.public import CrfContextAdapter
from apps.study.infrastructure.repositories.subject_export import (
    DjangoSubjectExportFieldCatalogRepository,
)


class SubjectExportFieldCatalogService:
    repository_class = DjangoSubjectExportFieldCatalogRepository
    crf_context_adapter_class = CrfContextAdapter

    def __init__(self, repository=None, crf_context_adapter=None):
        self.repository = repository or self.repository_class()
        self.crf_context_adapter = (
            crf_context_adapter or self.crf_context_adapter_class()
        )

    def list_groups(self, *, study_id: int, language_code="en") -> list[dict]:
        study_version = self.repository.resolve_active_study_version(
            study_id=study_id,
        )
        if not study_version:
            return []

        bindings = list(
            self.repository.list_enabled_bindings(
                study_id=study_id,
                study_version=study_version,
            )
        )
        fields_by_template_id = self.crf_context_adapter.list_export_fields_by_template_ids(
            template_ids={int(binding.form_definition.pk) for binding in bindings},
            language_code=language_code,
        )

        groups_by_event_id: dict[int, dict] = {}
        for binding in bindings:
            event = binding.event_definition
            form = binding.form_definition
            form_name = self._translated_form_name(form)
            event_group = groups_by_event_id.setdefault(
                int(event.pk),
                {
                    "event_definition_id": int(event.pk),
                    "event_code": event.code,
                    "event_name": event.name,
                    "forms": [],
                },
            )
            form_fields = []
            for field in fields_by_template_id.get(int(form.pk), ()):
                field_template_id = int(field["id"])
                field_key = str(field["field_key"])
                form_fields.append(
                    {
                        "token": f"{int(binding.pk)}:{field_template_id}",
                        "binding_id": int(binding.pk),
                        "event_definition_id": int(event.pk),
                        "crf_template_id": int(form.pk),
                        "field_template_id": field_template_id,
                        "event_code": event.code,
                        "event_name": event.name,
                        "crf_code": form.code,
                        "crf_name": form_name,
                        "is_repeatable_within_event": bool(
                            binding.is_repeatable_within_event
                        ),
                        "control_type": field.get("control_type") or "",
                        "choice_labels": field.get("choice_labels") or {},
                        "field_key": field_key,
                        "field_label": field.get("label") or field_key,
                        "header": f"{event.code}.{form.code}.{field_key}",
                    }
                )
            if form_fields:
                event_group["forms"].append(
                    {
                        "binding_id": int(binding.pk),
                        "crf_code": form.code,
                        "crf_name": form_name,
                        "fields": form_fields,
                    }
                )
        return list(groups_by_event_id.values())

    @staticmethod
    def flatten_groups(groups: list[dict]) -> tuple[dict, ...]:
        return tuple(
            field
            for group in groups
            for form in group["forms"]
            for field in form["fields"]
        )

    @staticmethod
    def _translated_form_name(form) -> str:
        if hasattr(form, "safe_translation_getter"):
            return str(
                form.safe_translation_getter(
                    "name",
                    any_language=True,
                )
                or form.code
            )
        return str(getattr(form, "name", "") or form.code)


__all__ = ["SubjectExportFieldCatalogService"]

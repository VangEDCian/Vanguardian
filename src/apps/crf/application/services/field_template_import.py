from django.db import transaction
from django.utils import timezone

from apps.crf.domain.exceptions import FormBuilderDomainValidationError
from apps.crf.infrastructure.repositories import DjangoCrfFieldTemplateImportRepository


class CrfFieldTemplateImportAmbiguousError(FormBuilderDomainValidationError):
    """Raised when an import row resolves to more than one CRF object."""


class CrfFieldTemplateImportNotFoundError(FormBuilderDomainValidationError):
    """Raised when an import row cannot resolve a referenced CRF object."""


class CrfFieldTemplateImportService:
    repository_class = DjangoCrfFieldTemplateImportRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def resolve_template_by_name_or_code(self, *, study_id, form_name):
        templates = list(
            self.repository.find_templates_by_name_or_code(
                study_id=study_id,
                form_name=form_name,
            )
        )
        if not templates:
            raise CrfFieldTemplateImportNotFoundError(
                f"Form Name '{form_name}' was not found in this study."
            )
        if len(templates) > 1:
            raise CrfFieldTemplateImportAmbiguousError(
                f"Form Name '{form_name}' is ambiguous in this study."
            )
        return templates[0]

    def resolve_section_by_name_or_code(self, *, crf_template_id, section_name):
        sections = list(
            self.repository.find_sections_by_name_or_code(
                crf_template_id=crf_template_id,
                section_name=section_name,
            )
        )
        if not sections:
            raise CrfFieldTemplateImportNotFoundError(
                f"Section Name '{section_name}' was not found in this form."
            )
        if len(sections) > 1:
            raise CrfFieldTemplateImportAmbiguousError(
                f"Section Name '{section_name}' is ambiguous in this form."
            )
        return sections[0]

    @transaction.atomic
    def reset_template_fields_for_import(self, *, crf_template_id, actor_user_id, now=None):
        now = now or timezone.now()
        return self.repository.reset_template_fields_for_import(
            crf_template_id=crf_template_id,
            actor_user_id=actor_user_id,
            now=now,
        )

    @transaction.atomic
    def upsert_template_field(self, *, crf_template_id, section_template_id, payload, actor_user_id, now=None):
        now = now or timezone.now()
        field_template = self.repository.get_field_template_for_import(
            crf_template_id=crf_template_id,
            field_key=payload["field_key"],
        )
        action = "updated"
        if field_template is None:
            action = "created"
            field_template = self.repository.build_field_template(
                crf_template_id=crf_template_id,
                field_key=payload["field_key"],
                created_at=now,
                created_by_id=actor_user_id,
            )

        field_template.data_type = payload["data_type"]
        field_template.is_active = True
        field_template.display_order = payload["display_order"]
        field_template.section_template_id = section_template_id
        field_template.deleted = False
        field_template.updated_at = now
        field_template.updated_by_id = actor_user_id
        self.repository.save_field_template(field_template)

        self._save_field_template_translations(field_template=field_template, payload=payload)
        definition = self._save_definition(field_template=field_template, payload=payload, actor_user_id=actor_user_id, now=now)
        ui_config = self._save_ui_config(field_template=field_template, payload=payload, actor_user_id=actor_user_id, now=now)
        self._save_definition_translations(definition=definition, payload=payload)
        self._save_ui_config_translations(ui_config=ui_config, payload=payload)
        return action, field_template

    def _save_field_template_translations(self, *, field_template, payload):
        fallback_label = payload["label_en"] or payload["label_vi"] or payload["field_key"]
        self.repository.save_field_template_translation(
            field_template=field_template,
            language_code="en",
            label=payload["label_en"] or fallback_label,
        )
        self.repository.save_field_template_translation(
            field_template=field_template,
            language_code="vi",
            label=payload["label_vi"] or fallback_label,
        )

    def _save_definition(self, *, field_template, payload, actor_user_id, now):
        return self.repository.save_field_definition(
            field_template=field_template,
            values={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "sdtm": payload["sdtm"],
                "range_min": payload["range_min"],
                "range_max": payload["range_max"],
                "precision": payload["precision"],
                "allowed_missing_values": payload["allowed_missing_values"] or "",
                "data_semantic": payload["data_semantic"],
                "text_max_length": payload["text_max_length"],
                "text_min_length": payload["text_min_length"],
                "pattern": payload["pattern"],
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            },
        )

    def _save_definition_translations(self, *, definition, payload):
        for language_code in ("en", "vi"):
            self.repository.save_field_definition_translation(
                definition=definition,
                language_code=language_code,
                values={
                    "unit": payload[f"unit_{language_code}"],
                    "codelist": payload[f"codelist_{language_code}"],
                    "comments": payload[f"comments_{language_code}"],
                    "pattern_err_msg": payload[f"pattern_err_msg_{language_code}"],
                },
            )

    def _save_ui_config(self, *, field_template, payload, actor_user_id, now):
        return self.repository.save_field_ui_config(
            field_template=field_template,
            values={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "control_type": payload["control_type"],
                "control_layout": payload["control_layout"] or "normal",
                "layout": payload["layout"],
                "behavior": payload["behavior"],
                "style": payload["style"],
                "classes": payload["classes"],
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            },
        )

    def _save_ui_config_translations(self, *, ui_config, payload):
        for language_code in ("en", "vi"):
            self.repository.save_field_ui_config_translation(
                ui_config=ui_config,
                language_code=language_code,
                values={
                    "text": payload[f"text_{language_code}"],
                    "options": payload[f"options_{language_code}"],
                },
            )


__all__ = [
    "CrfFieldTemplateImportAmbiguousError",
    "CrfFieldTemplateImportNotFoundError",
    "CrfFieldTemplateImportService",
]

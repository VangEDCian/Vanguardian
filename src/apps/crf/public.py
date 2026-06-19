import json

from apps.crf.application import (
    CrfTemplateAmbiguousError,
    CrfTemplateApplicationService,
    CrfTemplateNotFoundError,
)
from apps.crf.application.services import CrfFieldTemplateImportService
from apps.crf.application.services.validation_rule_import import CrfValidationRuleImportService
from apps.crf.models import CrfSectionTemplate


class CrfContextAdapter:
    def __init__(self, crf_template_service=None, field_template_import_service=None, validation_rule_import_service=None):
        self.crf_template_service = crf_template_service or CrfTemplateApplicationService()
        self.field_template_import_service = field_template_import_service or CrfFieldTemplateImportService()
        self.validation_rule_import_service = validation_rule_import_service or CrfValidationRuleImportService()

    def get_crf_template_model(self):
        return self.crf_template_service.get_crf_template_model()

    def list_study_templates_for_listing(self, *, study_id):
        return self.crf_template_service.list_study_templates_for_listing(study_id=study_id)

    def list_study_templates_by_code(self, *, study_id, code):
        return self.crf_template_service.list_study_templates_by_code(
            study_id=study_id,
            code=code,
        )

    def list_study_crf_navigation(self, *, study_id):
        return self.crf_template_service.list_study_crf_navigation(study_id=study_id)

    def list_template_fields_with_ui_config(self, *, template_id):
        return self.crf_template_service.list_template_fields_with_ui_config(
            template_id=template_id,
        )

    def list_template_field_schema_for_display_label(self, *, template_id):
        fields = self.list_template_fields_with_ui_config(template_id=template_id)
        return [
            {
                "field_key": field["field_key"],
                "label": field["label"],
                "data_type": field["data_type"],
                "ui_config": field.get("ui_config") or {},
            }
            for field in fields
        ]

    def resolve_choice_display_label(
        self,
        *,
        template_id,
        field_key,
        raw_value,
        language_code="en",
    ):
        normalized_value = "" if raw_value is None else str(raw_value).strip()
        if not normalized_value:
            return normalized_value
        fields = self.list_template_fields_with_ui_config(template_id=template_id)
        target_field = next((field for field in fields if field["field_key"] == field_key), None)
        if target_field is None:
            return normalized_value
        options = self._normalize_choice_options(
            (target_field.get("ui_config") or {}).get("options"),
        )
        if not options:
            return normalized_value
        label_map = {
            str(option.get("value", "")).strip(): str(option.get("label", "")).strip()
            for option in options
        }
        selected_values = [item.strip() for item in normalized_value.split(",") if item.strip()]
        resolved = [label_map.get(value, value) for value in selected_values]
        if not resolved:
            return normalized_value
        return ", ".join(resolved)

    @staticmethod
    def _normalize_choice_options(raw_options):
        if not raw_options:
            return []
        if isinstance(raw_options, list):
            return raw_options
        if isinstance(raw_options, str):
            normalized = raw_options.strip()
            if normalized.startswith("["):
                try:
                    parsed = json.loads(normalized)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return parsed
            options = []
            for chunk in normalized.split():
                if "=" in chunk:
                    label, value = chunk.split("=", 1)
                    options.append({"label": label.strip(), "value": value.strip()})
            return options
        return []

    def resolve_unique_template_by_code(self, *, study_id, code, case_insensitive=False):
        return self.crf_template_service.resolve_unique_template_by_code(
            study_id=study_id,
            code=code,
            case_insensitive=case_insensitive,
        )

    def resolve_unique_template_by_code_version(self, *, study_id, code, version):
        return self.crf_template_service.resolve_unique_template_by_code_version(
            study_id=study_id,
            code=code,
            version=version,
        )

    def upsert_crf_template(
        self,
        *,
        selected_study_id,
        study_id,
        code,
        version,
        vi_name,
        en_name,
        actor_user_id,
        now=None,
    ):
        return self.crf_template_service.upsert_crf_template(
            selected_study_id=selected_study_id,
            study_id=study_id,
            code=code,
            version=version,
            vi_name=vi_name,
            en_name=en_name,
            actor_user_id=actor_user_id,
            now=now,
        )

    def upsert_section_template(
        self,
        *,
        selected_study_id,
        crf_template_id,
        section_template_id=None,
        section_code,
        vi_name,
        en_name,
        vi_description=None,
        en_description=None,
        vi_help_text=None,
        en_help_text=None,
        vi_instruction_text=None,
        en_instruction_text=None,
        display_order,
        is_required,
        is_repeatable,
        min_repeats,
        max_repeats,
        actor_user_id,
        now=None,
    ):
        is_legacy_import_contract = (
            section_template_id is None
            and vi_description is None
            and en_description is None
            and vi_help_text is None
            and en_help_text is None
            and vi_instruction_text is None
            and en_instruction_text is None
        )

        import_outcome = None
        resolved_section_template_id = section_template_id
        if resolved_section_template_id is None:
            existing_section_template = CrfSectionTemplate.objects.filter(
                crf_template_id=crf_template_id,
                section_code=section_code,
            ).first()
            if existing_section_template is not None:
                resolved_section_template_id = existing_section_template.pk
                import_outcome = "updated"
            else:
                import_outcome = "created"

        result = self.crf_template_service.upsert_section_template(
            selected_study_id=selected_study_id,
            crf_template_id=crf_template_id,
            section_template_id=resolved_section_template_id,
            section_code=section_code,
            vi_name=vi_name,
            en_name=en_name,
            vi_description=vi_description or "",
            en_description=en_description or "",
            vi_help_text=vi_help_text or "",
            en_help_text=en_help_text or "",
            vi_instruction_text=vi_instruction_text or "",
            en_instruction_text=en_instruction_text or "",
            display_order=display_order,
            is_required=is_required,
            is_repeatable=is_repeatable,
            min_repeats=min_repeats,
            max_repeats=max_repeats,
            actor_user_id=actor_user_id,
            now=now,
        )
        if is_legacy_import_contract:
            return import_outcome or "updated"
        return result

    def resolve_import_template_by_name_or_code(self, *, study_id, form_name):
        return self.field_template_import_service.resolve_template_by_name_or_code(
            study_id=study_id,
            form_name=form_name,
        )

    def resolve_import_section_by_name_or_code(self, *, crf_template_id, section_name):
        return self.field_template_import_service.resolve_section_by_name_or_code(
            crf_template_id=crf_template_id,
            section_name=section_name,
        )

    def resolve_import_validation_rule_template_by_code_or_id(self, *, study_id, form_code):
        return self.validation_rule_import_service.resolve_template_by_code_or_id(
            study_id=study_id,
            form_code=form_code,
        )

    def resolve_import_validation_rule_template_by_code(self, *, study_id, form_code):
        return self.validation_rule_import_service.resolve_template_by_code(
            study_id=study_id,
            form_code=form_code,
        )

    def resolve_import_validation_rule_field_by_name_or_id(self, *, crf_template_id, field_name):
        return self.validation_rule_import_service.resolve_field_by_name_or_id(
            crf_template_id=crf_template_id,
            field_name=field_name,
        )

    def resolve_import_validation_rule_field_by_key(self, *, crf_template_id, field_name):
        return self.validation_rule_import_service.resolve_field_by_key(
            crf_template_id=crf_template_id,
            field_name=field_name,
        )

    def reset_import_template_fields(
        self,
        *,
        crf_template_id,
        actor_user_id,
        now=None,
    ):
        return self.field_template_import_service.reset_template_fields_for_import(
            crf_template_id=crf_template_id,
            actor_user_id=actor_user_id,
            now=now,
        )

    def upsert_import_template_field(
        self,
        *,
        crf_template_id,
        section_template_id,
        payload,
        actor_user_id,
        now=None,
    ):
        return self.field_template_import_service.upsert_template_field(
            crf_template_id=crf_template_id,
            section_template_id=section_template_id,
            payload=payload,
            actor_user_id=actor_user_id,
            now=now,
        )

    def upsert_import_validation_rule(
        self,
        *,
        study_id,
        crf_template_id,
        field_template_id,
        rule_type,
        expression,
        severity,
        mode,
        vi_message,
        en_message,
        actor_user_id,
        now=None,
    ):
        return self.validation_rule_import_service.upsert_validation_rule(
            study_id=study_id,
            crf_template_id=crf_template_id,
            field_template_id=field_template_id,
            rule_type=rule_type,
            expression=expression,
            severity=severity,
            mode=mode,
            vi_message=vi_message,
            en_message=en_message,
            actor_user_id=actor_user_id,
            now=now,
        )

    def reset_import_validation_rules(
        self,
        *,
        field_template_ids,
        actor_user_id,
        now=None,
    ):
        return self.validation_rule_import_service.reset_validation_rules_for_import(
            field_template_ids=field_template_ids,
            actor_user_id=actor_user_id,
            now=now,
        )

    def upsert_section_layout_config(
        self,
        *,
        selected_study_id,
        section_template_id,
        layout_type,
        column_count,
        label_position,
        density,
        section_style,
        is_collapsible,
        is_expanded_by_default,
        show_section_header,
        show_border,
        show_background,
        custom_css_class,
        custom_layout_schema,
        actor_user_id,
        now=None,
    ):
        return self.crf_template_service.upsert_section_layout_config(
            selected_study_id=selected_study_id,
            section_template_id=section_template_id,
            layout_type=layout_type,
            column_count=column_count,
            label_position=label_position,
            density=density,
            section_style=section_style,
            is_collapsible=is_collapsible,
            is_expanded_by_default=is_expanded_by_default,
            show_section_header=show_section_header,
            show_border=show_border,
            show_background=show_background,
            custom_css_class=custom_css_class,
            custom_layout_schema=custom_layout_schema,
            actor_user_id=actor_user_id,
            now=now,
        )


def get_crf_template_model():
    return CrfContextAdapter().get_crf_template_model()


__all__ = [
    "CrfContextAdapter",
    "CrfTemplateNotFoundError",
    "CrfTemplateAmbiguousError",
    "get_crf_template_model",
]

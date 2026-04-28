import json

from django.http import Http404

from apps.crf.domain.exceptions import FormScopeViolationError
from apps.crf.presentation.web.forms import (
    CrfFieldCreateForm,
    CrfFieldUpdateForm,
    CrfSectionTemplateForm,
    CrfTemplateTranslationForm,
)
from apps.shared.context_processors import StudyDropdownHandler


class CrfFormBuilderSupportMixin:
    @staticmethod
    def _bind_field_domain_error(form, exc):
        message = str(exc or "")
        normalized_message = message.lower()
        is_duplicate_field_key = (
            "field_key must be unique in form scope." in message
            or "crf_fieldtemplate_crf_template_fieldkey_uniq" in normalized_message
            or "duplicate entry" in normalized_message and "fieldkey" in normalized_message
        )

        if is_duplicate_field_key:
            form.add_error("field_key", "Field Key da ton tai trong form nay.")
            return

        form.add_error(None, message)

    def get_read_model_service(self):
        return self.read_model_service_class()

    def get_orchestration_service(self):
        return self.orchestration_service_class()

    def get_template_service(self):
        return self.template_service_class()

    def get_audit_service(self):
        return self.audit_service_class()

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_create_field_form(self):
        if not hasattr(self, "_create_field_form"):
            self._create_field_form = CrfFieldCreateForm()
        return self._create_field_form

    def get_update_field_form(self):
        if not hasattr(self, "_update_field_form"):
            self._update_field_form = CrfFieldUpdateForm()
        return self._update_field_form

    def get_section_template_form(self, *, initial=None):
        if not hasattr(self, "_section_template_form"):
            self._section_template_form = CrfSectionTemplateForm(initial=initial, prefix=self.section_form_prefix)
        return self._section_template_form

    def get_template_translation_form(self, *, initial=None):
        if not hasattr(self, "_template_translation_form"):
            self._template_translation_form = CrfTemplateTranslationForm(initial=initial)
        return self._template_translation_form

    def get_selected_study_id(self):
        return StudyDropdownHandler(request=self.request).build().selected_id

    def get_builder(self):
        if not hasattr(self, "_builder"):
            try:
                self._builder = self.get_read_model_service().get_builder(
                    form_id=self.kwargs["form_id"],
                )
            except FormScopeViolationError as exc:
                raise Http404 from exc
        return self._builder

    def ensure_study_scope(self, builder):
        selected_study_id = self.get_selected_study_id()
        if selected_study_id is None:
            raise Http404
        if int(builder["template"]["study_id"]) != int(selected_study_id):
            raise Http404
        return selected_study_id

    def get_section_choices(self, builder):
        sections = builder.get("sections", [])
        choices = []
        for section in sections:
            section_id = section.get("id")
            if section_id is None:
                continue
            choices.append((str(section_id), f'{section.get("section_code", "")}: {section.get("section_name", "")}'))
        return choices

    def get_section_template_initial(self, builder):
        section_id = self.request.GET.get("section_id")
        if not section_id:
            return {}

        for section in builder.get("sections", []):
            if str(section.get("id")) != str(section_id):
                continue

            translations = section.get("translations", {}) or {}
            en_translation = translations.get("en", {}) or {}
            vi_translation = translations.get("vi", {}) or {}
            return {
                "section_template_id": section.get("id"),
                "section_code": section.get("section_code", ""),
                "section_name_en": en_translation.get("section_name", section.get("section_name", "")),
                "section_name_vi": vi_translation.get("section_name", section.get("section_name", "")),
                "description_en": en_translation.get("description", ""),
                "description_vi": vi_translation.get("description", ""),
                "help_text_en": en_translation.get("help_text", ""),
                "help_text_vi": vi_translation.get("help_text", ""),
                "instruction_text_en": en_translation.get("instruction_text", ""),
                "instruction_text_vi": vi_translation.get("instruction_text", ""),
                "display_order": section.get("display_order", 1),
                "is_required": section.get("is_required", True),
                "is_repeatable": section.get("is_repeatable", False),
                "min_repeats": section.get("min_repeats", 0),
                "max_repeats": section.get("max_repeats"),
            }

        return {}

    def get_template_translation_initial(self, builder):
        template = builder.get("template", {}) or {}
        translations = template.get("translations", {}) or {}
        en_translation = translations.get("en", "") if isinstance(translations.get("en"), str) else translations.get("en", {})
        vi_translation = translations.get("vi", "") if isinstance(translations.get("vi"), str) else translations.get("vi", {})
        return {
            "template_id": template.get("id"),
            "code": template.get("code", ""),
            "version": template.get("version", ""),
            "name_en": en_translation if isinstance(en_translation, str) else template.get("name", ""),
            "name_vi": vi_translation if isinstance(vi_translation, str) else template.get("name", ""),
        }

    @staticmethod
    def _parse_optional_int(raw_value):
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def get_selected_field_id(self):
        raw_value = self.request.GET.get("field_id") or self.request.POST.get("field_id")
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def get_selected_section_id(self):
        raw_value = self.request.GET.get("section_id") or self.request.POST.get("section_id")
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def get_selected_section(self, builder):
        selected_section_id = self.get_selected_section_id()
        if selected_section_id is None:
            return None

        for section in builder.get("sections", []):
            if int(section.get("id") or 0) == selected_section_id:
                return section

        return None

    def get_selected_field(self, builder):
        selected_field_id = self.get_selected_field_id()
        if selected_field_id is None:
            return None

        for field in builder.get("fields", []):
            if int(field.get("id") or 0) == selected_field_id:
                return field

        return None

    def get_selected_field_initial(self, builder):
        selected_field_id = self.get_selected_field_id()
        if selected_field_id is None:
            return {}

        for field in builder.get("fields", []):
            if int(field.get("id") or 0) != selected_field_id:
                continue

            field_template = field.get("field_template", {}) or {}
            field_definition = field.get("field_definition", {}) or {}
            field_ui_config = field.get("field_ui_config", {}) or {}
            validation_rules = field.get("field_validation_rules", []) or []
            translations = field_template.get("translations", {}) or {}
            return {
                "field_id": field.get("id"),
                "field_key": field_template.get("field_key", ""),
                "data_type": field_template.get("data_type", ""),
                "is_active": field_template.get("is_active", True),
                "display_order": field_template.get("display_order", 1),
                "section_template_id": field_template.get("section_template_id"),
                "label_en": translations.get("en", field_template.get("label", "")),
                "label_vi": translations.get("vi", field_template.get("label", "")),
                "sdtm": json.dumps(field_definition.get("sdtm") or {}, ensure_ascii=False),
                "unit": field_definition.get("unit", "") or "",
                "range_min": field_definition.get("range_min"),
                "range_max": field_definition.get("range_max"),
                "precision": field_definition.get("precision"),
                "allowed_missing_values": field_definition.get("allowed_missing_values", "") or "",
                "codelist": field_definition.get("codelist", "") or "",
                "data_semantic": field_definition.get("data_semantic", "") or "",
                "comments": field_definition.get("comments", "") or "",
                "text_max_length": field_definition.get("text_max_length"),
                "text_min_length": field_definition.get("text_min_length"),
                "pattern": field_definition.get("pattern", "") or "",
                "pattern_err_msg": field_definition.get("pattern_err_msg", "") or "",
                "control_type": field_ui_config.get("control_type", "") or "",
                "layout": field_ui_config.get("layout", "") or "",
                "text": field_ui_config.get("text", "") or "",
                "behavior": field_ui_config.get("behavior", "") or "",
                "options": field_ui_config.get("options", "") or "",
                "style": field_ui_config.get("style", "") or "",
                "validation_rules_json": json.dumps([
                    {
                        "id": rule.get("id"),
                        "rule_type": rule.get("rule_type"),
                        "expression": rule.get("expression"),
                        "severity": rule.get("severity"),
                        "mode": rule.get("mode"),
                        "messages": rule.get("messages", {}) or {},
                    }
                    for rule in validation_rules
                ], ensure_ascii=False),
            }

        return {}

    def apply_section_choices(self, form, builder):
        choices = self.get_section_choices(builder)
        if hasattr(form, "set_section_template_choices"):
            form.set_section_template_choices(choices)
        return form

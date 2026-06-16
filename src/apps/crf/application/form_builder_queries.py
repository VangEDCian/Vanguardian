import json

from django.utils.translation import get_language

from apps.crf.domain.exceptions import FormScopeViolationError
from apps.crf.infrastructure.repositories import DjangoOrmFormBuilderRepository


class FormBuilderReadModelService:
    repository_class = DjangoOrmFormBuilderRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @staticmethod
    def _current_language_code():
        return FormBuilderReadModelService._normalize_language_code(get_language())

    def get_builder(self, *, form_id):
        form = self.repository.get_form_builder_aggregate(form_id=form_id)
        if form is None:
            raise FormScopeViolationError("Form is not found.")

        current_language = self._current_language_code()
        fields = getattr(form, "field_templates", []).all()
        sections = getattr(form, "section_templates", []).all()
        payload_fields = [self._serialize_field(field) for field in fields]
        payload_sections = [self._serialize_section_with_fields(section, payload_fields) for section in sections]
        unassigned_fields = [field for field in payload_fields if field["field_template"]["section"] is None]
        if unassigned_fields:
            payload_sections.append(
                {
                    "id": None,
                    "section_code": "UNASSIGNED",
                    "section_name": "Unassigned",
                    "display_order": 999999,
                    "is_required": False,
                    "is_enabled": True,
                    "is_repeatable": False,
                    "min_repeats": 0,
                    "max_repeats": None,
                    "translations": {},
                    "fields": unassigned_fields,
                }
            )

        payload_sections.sort(key=lambda item: (item["display_order"], item["section_name"], item["section_code"] or ""))

        return {
            "template": {
                "id": form.pk,
                "code": form.code,
                "name": self._translated_value(form, current_language, "name", default=form.code),
                "translations": self._serialize_translations(form, "name"),
                "version": form.version,
                "is_active": bool(form.is_active),
                "study_id": form.study_id,
            },
            "form": {
                "id": form.pk,
                "code": form.code,
                "name": self._translated_value(form, current_language, "name", default=form.code),
                "translations": self._serialize_translations(form, "name"),
                "version": form.version,
                "is_active": bool(form.is_active),
                "study_id": form.study_id,
            },
            "fields": payload_fields,
            "sections": payload_sections,
        }

    def _serialize_field(self, field):
        current_language = self._current_language_code()
        definition = getattr(field, "definition", None)
        ui_config = getattr(field, "ui_config", None)
        rules = list(field.validation_rules.all())

        return {
            "id": field.pk,
            "field_template": {
                "field_key": field.field_key,
                "data_type": field.data_type,
                "is_active": bool(field.is_active),
                "display_order": field.display_order,
                "section_template_id": field.section_template_id,
                "label": self._translated_value(field, current_language, "label", default=field.field_key),
                "translations": self._serialize_translations(field, "label"),
                "section": self._serialize_section(field.section_template),
            },
            "field_definition": {
                "sdtm": self._safe_json(definition.sdtm if definition else ""),
                "unit": self._translated_related_value(definition, current_language, "unit"),
                "range_min": definition.range_min if definition else None,
                "range_max": definition.range_max if definition else None,
                "precision": definition.precision if definition else None,
                "allowed_missing_values": definition.allowed_missing_values if definition else "",
                "codelist": self._translated_related_value(definition, current_language, "codelist"),
                "data_semantic": definition.data_semantic if definition else None,
                "comments": self._translated_related_value(definition, current_language, "comments"),
                "text_max_length": definition.text_max_length if definition else None,
                "text_min_length": definition.text_min_length if definition else None,
                "pattern": definition.pattern if definition else None,
                "pattern_err_msg": self._translated_related_value(definition, current_language, "pattern_err_msg"),
            },
            "field_ui_config": {
                "control_type": ui_config.control_type if ui_config else None,
                "layout": ui_config.layout if ui_config else None,
                "text": self._translated_related_value(ui_config, current_language, "text"),
                "behavior": ui_config.behavior if ui_config else None,
                "options": self._translated_related_value(ui_config, current_language, "options"),
                "style": ui_config.style if ui_config else None,
            },
            "field_validation_rules": [
                {
                    "id": rule.pk,
                    "rule_type": rule.rule_type,
                    "expression": rule.expression,
                    "severity": rule.severity,
                    "mode": rule.mode,
                    "message": self._translated_value(rule, current_language, "message", default=""),
                    "messages": self._serialize_rule_translations(rule),
                }
                for rule in rules
            ],
        }

    def _serialize_section(self, section):
        if section is None:
            return None

        return {
            "id": section.pk,
            "section_code": section.section_code,
            "section_name": section.safe_translation_getter("section_name", default=section.section_code, any_language=True),
            "translations": self._serialize_section_translations(section),
            "display_order": section.display_order,
            "is_required": bool(section.is_required),
            "is_enabled": bool(section.is_enabled),
            "is_repeatable": bool(section.is_repeatable),
            "min_repeats": section.min_repeats,
            "max_repeats": section.max_repeats,
        }

    def _serialize_section_with_fields(self, section, payload_fields):
        serialized_section = self._serialize_section(section)
        if serialized_section is None:
            return {
                "id": None,
                "section_code": "UNASSIGNED",
                "section_name": "Unassigned",
                "display_order": 999999,
                "is_required": False,
                "is_enabled": True,
                "is_repeatable": False,
                "min_repeats": 0,
                "max_repeats": None,
                "translations": {},
                "fields": [],
            }

        serialized_section["fields"] = [
            field
            for field in payload_fields
            if field["field_template"]["section_template_id"] == serialized_section["id"]
        ]
        return serialized_section

    @staticmethod
    def _serialize_section_translations(section):
        translations = {}
        for translation in getattr(section, "translations", []).all():
            language_code = str(translation.language_code).strip().lower()
            if not language_code:
                continue
            translations[language_code] = {
                "section_name": translation.section_name or "",
                "description": translation.description or "",
                "help_text": translation.help_text or "",
                "instruction_text": translation.instruction_text or "",
            }
        return translations

    @staticmethod
    def _safe_json(raw):
        source = (raw or "").strip()
        if not source:
            return {"domain": "", "variable": "", "role": ""}
        try:
            parsed = json.loads(source)
        except json.JSONDecodeError:
            return {"domain": "", "variable": "", "role": ""}
        if isinstance(parsed, dict):
            return parsed
        return {"domain": "", "variable": "", "role": ""}

    @staticmethod
    def _translated_value(instance, lang_code, field_name, default=""):
        language_code = FormBuilderReadModelService._normalize_language_code(lang_code)
        if hasattr(instance, "safe_translation_getter"):
            value = instance.safe_translation_getter(
                field_name,
                default=default,
                language_code=language_code,
                any_language=False,
            )
            if value not in (None, ""):
                return value
            fallback = instance.safe_translation_getter(
                field_name,
                default=default,
                any_language=True,
            )
            return fallback or default

        return getattr(instance, field_name, default) or default

    @staticmethod
    def _translated_related_value(instance, lang_code, field_name, default=None):
        if instance is None:
            return default

        language_code = FormBuilderReadModelService._normalize_language_code(lang_code)
        translations = list(getattr(getattr(instance, "translations", None), "all", lambda: [])())
        translation_by_language = {
            str(translation.language_code).strip().lower(): translation
            for translation in translations
        }

        for candidate_language in (language_code, "en"):
            translation = translation_by_language.get(candidate_language)
            if translation is None:
                continue
            value = getattr(translation, field_name, default)
            if value not in (None, ""):
                return value

        for translation in translations:
            value = getattr(translation, field_name, default)
            if value not in (None, ""):
                return value
        return default

    @staticmethod
    def _serialize_translations(instance, field_name):
        translations = {}
        for translation in getattr(instance, "translations", []).all():
            translations[str(translation.language_code).strip().lower()] = getattr(translation, field_name, "") or ""
        return translations

    @staticmethod
    def _normalize_language_code(language_code):
        normalized = (language_code or get_language() or "en").strip().lower()
        return normalized.split("-", 1)[0]

    @staticmethod
    def _serialize_rule_translations(rule):
        translations = FormBuilderReadModelService._serialize_translations(rule, "message")
        if not translations and hasattr(rule, "safe_translation_getter"):
            translations["en"] = rule.safe_translation_getter("message", default="", language_code="en") or ""
        return translations

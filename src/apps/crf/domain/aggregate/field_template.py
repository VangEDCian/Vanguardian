import json
import re
from dataclasses import dataclass, field
from decimal import Decimal

from apps.crf.domain.aggregate.entities import CrfFieldTemplateEntity
from apps.crf.domain.aggregate.sections import (
    FieldDefinitionSection,
    FieldUiConfigSection,
    FieldValidationRuleSection,
    FieldValidationRuleTranslationSection,
)
from apps.crf.domain.exceptions import FormBuilderDomainValidationError


@dataclass(frozen=True)
class FieldTemplateAggregate:
    field_template: CrfFieldTemplateEntity
    field_definition: FieldDefinitionSection
    field_ui_config: FieldUiConfigSection
    field_validation_rules: tuple[FieldValidationRuleSection, ...] = field(default_factory=tuple)
    field_keys_in_form: tuple[str, ...] = field(default_factory=tuple)

    CONTROL_TYPE_BY_DATA_TYPE = {
        "BOOLEAN": "checkbox_list",
        "CODELIST": "dropdown",
        "DATE": "date_picker",
        "DATETIME": "date_picker",
        "DECIMAL": "entry_box",
        "INTEGER": "entry_box",
        "NUMBER": "entry_box",
        "STRING": "dropdown",
        "TEXT": "entry_box",
        "TEXTAREA": "text_area",
        "TIME": "time_picker",
    }

    CONTROL_TYPE_ALIASES = {
        "checkbox": "checkbox_list",
        "checkbox list": "checkbox_list",
        "date": "date_picker",
        "date picker": "date_picker",
        "datetime": "date_picker",
        "dropdown": "dropdown",
        "dropdown list": "dropdown",
        "entry box": "entry_box",
        "select2": "select2",
        "select 2": "select2",
        "select": "dropdown",
        "text": "entry_box",
        "text box": "entry_box",
        "text area": "text_area",
        "textarea": "text_area",
        "text_input": "entry_box",
        "time": "time_picker",
        "time picker": "time_picker",
        "date_text": "date_text",
        "date text": "date_text",
        "datetime_text": "datetime_text",
        "datetime text": "datetime_text",
        "radio": "radio_button_list",
        "radio button list": "radio_button_list",
    }

    ALLOWED_CONTROL_TYPES_BY_DATA_TYPE = {
        "DATE": {"date_picker", "date_text"},
        "DATETIME": {"date_picker", "datetime_text"},
    }
    VALIDATION_RULE_TYPE_ALIASES = {
        "custom": "CUSTOM_EXPRESSION",
        "custom expression": "CUSTOM_EXPRESSION",
        "custom_expression": "CUSTOM_EXPRESSION",
        "required": "REQUIRED",
    }
    VALIDATION_RULE_TYPES = set(VALIDATION_RULE_TYPE_ALIASES.values())
    VALIDATION_RULE_MODE_ALIASES = {
        "blocking": "HARD",
        "hard": "HARD",
        "query": "QUERY",
        "soft": "SOFT",
        "warning": "SOFT",
    }
    VALIDATION_RULE_MODES = set(VALIDATION_RULE_MODE_ALIASES.values())

    @classmethod
    def from_payload(
        cls,
        *,
        field_key,
        data_type,
        is_active,
        display_order,
        section_template_id,
        label_en,
        label_vi,
        definition,
        ui_config,
        validation_rules,
        field_keys_in_form=(),
    ):
        sdtm = cls._normalize_sdtm(definition.get("sdtm"))
        range_min = cls._to_decimal(definition.get("range_min"))
        range_max = cls._to_decimal(definition.get("range_max"))
        if range_min is not None and range_max is not None and range_min > range_max:
            raise FormBuilderDomainValidationError("range_min must be less than or equal to range_max.")

        field_template = CrfFieldTemplateEntity.from_payload(
            field_key=field_key,
            data_type=data_type,
            is_active=is_active,
            display_order=display_order,
            section_template_id=section_template_id,
            label_en=label_en,
            label_vi=label_vi,
        )
        cls._validate_field_key_uniqueness(field_template.field_key, field_keys_in_form)
        control_type = cls._normalize_control_type(ui_config.get("control_type"), field_template.data_type)

        definition_section = FieldDefinitionSection(
            sdtm=sdtm,
            unit=cls._nullable_text(definition.get("unit")),
            range_min=range_min,
            range_max=range_max,
            precision=cls._normalize_precision(definition.get("precision")),
            allowed_missing_values=(definition.get("allowed_missing_values") or "").strip(),
            codelist=cls._normalize_codelist(definition.get("codelist"), data_type=field_template.data_type),
            data_semantic=cls._nullable_text(definition.get("data_semantic")),
            comments=cls._nullable_text(definition.get("comments")),
            text_max_length=cls._to_int(definition.get("text_max_length")),
            text_min_length=cls._to_int(definition.get("text_min_length")),
            pattern=cls._normalize_pattern(definition.get("pattern")),
            pattern_err_msg=cls._nullable_text(definition.get("pattern_err_msg")),
        )

        ui_section = FieldUiConfigSection(
            control_type=control_type,
            layout=cls._nullable_text(ui_config.get("layout")),
            text=cls._nullable_text(ui_config.get("text")),
            behavior=cls._nullable_text(ui_config.get("behavior")),
            options=cls._normalize_options(ui_config.get("options"), control_type=control_type),
            style=cls._nullable_text(ui_config.get("style")),
        )

        normalized_rules = []
        for rule in validation_rules:
            normalized_rules.append(
                FieldValidationRuleSection(
                    id=rule.get("id"),
                    rule_type=cls._normalize_validation_rule_type(rule.get("rule_type")),
                    expression=cls._normalize_rule_expression(rule.get("expression")),
                    severity=(rule.get("severity") or "").strip() or "error",
                    mode=cls._normalize_validation_rule_mode(rule.get("mode")),
                    translations=cls._normalize_rule_translations(rule.get("messages") or rule.get("translations") or {}),
                )
            )

        return cls(
            field_template=field_template,
            field_definition=definition_section,
            field_ui_config=ui_section,
            field_validation_rules=tuple(normalized_rules),
            field_keys_in_form=tuple(field_keys_in_form or ()),
        )

    def to_persistence_payload(self):
        return {
            "field_template": self._field_template_payload(),
            "field_definition": self._field_definition_payload(),
            "field_ui_config": self._field_ui_config_payload(),
            "field_validation_rules": self._field_validation_rules_payload(),
        }

    def _field_template_payload(self):
        return {
            "field_key": self.field_template.field_key,
            "data_type": self.field_template.data_type,
            "is_active": self.field_template.is_active,
            "display_order": self.field_template.display_order,
            "section_template_id": self.field_template.section_template_id,
            "label_en": self.field_template.label_en,
            "label_vi": self.field_template.label_vi,
        }

    def _field_definition_payload(self):
        return {
            "sdtm": self.field_definition.sdtm,
            "unit": self.field_definition.unit,
            "range_min": self.field_definition.range_min,
            "range_max": self.field_definition.range_max,
            "precision": self.field_definition.precision,
            "allowed_missing_values": self.field_definition.allowed_missing_values,
            "codelist": self.field_definition.codelist,
            "data_semantic": self.field_definition.data_semantic,
            "comments": self.field_definition.comments,
            "text_max_length": self.field_definition.text_max_length,
            "text_min_length": self.field_definition.text_min_length,
            "pattern": self.field_definition.pattern,
            "pattern_err_msg": self.field_definition.pattern_err_msg,
        }

    def _field_ui_config_payload(self):
        return {
            "control_type": self.field_ui_config.control_type,
            "layout": self.field_ui_config.layout,
            "text": self.field_ui_config.text,
            "behavior": self.field_ui_config.behavior,
            "options": self.field_ui_config.options,
            "style": self.field_ui_config.style,
        }

    def _field_validation_rules_payload(self):
        return [
            {
                "id": rule.id,
                "rule_type": rule.rule_type,
                "expression": rule.expression,
                "severity": rule.severity,
                "mode": rule.mode,
                "translations": [
                    {
                        "language_code": translation.language_code,
                        "message": translation.message,
                    }
                    for translation in rule.translations
                ],
            }
            for rule in self.field_validation_rules
        ]

    @staticmethod
    def _validate_field_key_uniqueness(field_key, field_keys_in_form):
        normalized_new_key = str(field_key or "").strip().lower()
        normalized_existing_keys = {
            str(existing_key or "").strip().lower()
            for existing_key in (field_keys_in_form or ())
        }
        if normalized_new_key in normalized_existing_keys:
            raise FormBuilderDomainValidationError("field_key must be unique in form scope.")

    @staticmethod
    def _normalize_sdtm(raw):
        allowed_keys = ("domain", "variable", "role")
        if isinstance(raw, dict):
            parsed = raw
        else:
            source = (raw or "").strip()
            if not source:
                raise FormBuilderDomainValidationError("sdtm is required.")
            try:
                parsed = json.loads(source)
            except json.JSONDecodeError as exc:
                raise FormBuilderDomainValidationError("sdtm must be valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise FormBuilderDomainValidationError("sdtm must be a JSON object.")

        normalized = {key: "" for key in allowed_keys}
        for raw_key, value in parsed.items():
            normalized_key = str(raw_key).strip().lower()
            if normalized_key not in allowed_keys:
                continue
            normalized[normalized_key] = "" if value is None else str(value).strip()

        missing = [key for key in allowed_keys if not normalized[key]]
        if missing:
            raise FormBuilderDomainValidationError("sdtm must include fixed keys: domain, variable, role.")

        return normalized

    @classmethod
    def _normalize_precision(cls, value):
        normalized = cls._to_int(value)
        if normalized is None:
            return None
        if normalized < 0:
            raise FormBuilderDomainValidationError("precision must be greater than or equal to 0.")
        return normalized

    @staticmethod
    def _normalize_codelist(value, *, data_type):
        if value in (None, ""):
            if data_type == "CODELIST":
                raise FormBuilderDomainValidationError("codelist is required for CODELIST data_type.")
            return ""

        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)

        normalized = str(value).strip()
        if not normalized:
            if data_type == "CODELIST":
                raise FormBuilderDomainValidationError("codelist is required for CODELIST data_type.")
            return ""

        if normalized.startswith(("[", "{")):
            try:
                parsed = json.loads(normalized)
            except json.JSONDecodeError as exc:
                raise FormBuilderDomainValidationError("codelist must be valid JSON when using JSON syntax.") from exc
            if not isinstance(parsed, (list, dict)):
                raise FormBuilderDomainValidationError("codelist JSON must be an array or object.")
            return json.dumps(parsed, ensure_ascii=False, sort_keys=True)

        return normalized

    @staticmethod
    def _normalize_pattern(value):
        normalized = (value or "").strip()
        if not normalized:
            return None
        try:
            re.compile(normalized)
        except re.error as exc:
            raise FormBuilderDomainValidationError("pattern must be a valid regular expression.") from exc
        return normalized

    @classmethod
    def _normalize_control_type(cls, control_type, data_type):
        expected_control_type = cls.CONTROL_TYPE_BY_DATA_TYPE.get(data_type)
        if expected_control_type is None:
            raise FormBuilderDomainValidationError(f"Unsupported data_type for control_type validation: {data_type}.")

        raw_value = (control_type or "").strip()
        if not raw_value:
            return expected_control_type

        normalized_value = cls.CONTROL_TYPE_ALIASES.get(raw_value.lower(), raw_value.strip().lower().replace(" ", "_"))
        if normalized_value == "select2" and data_type in {"CODELIST", "STRING", "TEXT"}:
            return normalized_value

        allowed_control_types = cls.ALLOWED_CONTROL_TYPES_BY_DATA_TYPE.get(data_type, {expected_control_type})
        if normalized_value not in allowed_control_types:
            raise FormBuilderDomainValidationError(
                f"control_type must match data_type. Expected {expected_control_type} for {data_type}."
            )
        return normalized_value

    @classmethod
    def _normalize_validation_rule_type(cls, value):
        normalized = cls._nullable_text(value)
        if not normalized:
            return "CUSTOM_EXPRESSION"
        normalized_key = normalized.replace("-", "_").strip().lower()
        rule_type = cls.VALIDATION_RULE_TYPE_ALIASES.get(normalized_key, normalized_key.upper())
        if rule_type not in cls.VALIDATION_RULE_TYPES:
            raise FormBuilderDomainValidationError("validation rule_type is not supported.")
        return rule_type

    @classmethod
    def _normalize_validation_rule_mode(cls, value):
        normalized = cls._nullable_text(value)
        if not normalized:
            return "HARD"
        normalized_key = normalized.replace("-", "_").strip().lower()
        mode = cls.VALIDATION_RULE_MODE_ALIASES.get(normalized_key, normalized_key.upper())
        if mode not in cls.VALIDATION_RULE_MODES:
            raise FormBuilderDomainValidationError("validation rule mode is not supported.")
        return mode

    @classmethod
    def _normalize_options(cls, value, *, control_type):
        is_select2 = control_type == "select2"
        if value in (None, ""):
            cls._assert_select2_options_present(is_select2)
            return None

        parsed = cls._parse_options_input(value, is_select2=is_select2)
        if parsed is None:
            return None
        options_payload = cls._normalize_options_payload(parsed)
        if is_select2 and (options_payload["source"] != "lookup" or not options_payload["lookup"]):
            raise FormBuilderDomainValidationError(
                "SELECT2 requires options.source=lookup and options.lookup."
            )
        return options_payload

    @staticmethod
    def _assert_select2_options_present(is_select2):
        if is_select2:
            raise FormBuilderDomainValidationError(
                "SELECT2 requires options.source=lookup and options.lookup."
            )

    @classmethod
    def _parse_options_input(cls, value, *, is_select2):
        if isinstance(value, (list, dict)):
            return value

        normalized = str(value).strip()
        if not normalized:
            cls._assert_select2_options_present(is_select2)
            return None

        if not normalized.startswith(("[", "{")):
            return cls._static_options_from_text(normalized)

        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise FormBuilderDomainValidationError("options must be valid JSON when using JSON syntax.") from exc
        if not isinstance(parsed, (list, dict)):
            raise FormBuilderDomainValidationError("options JSON must be an array or object.")
        return parsed

    @classmethod
    def _normalize_options_payload(cls, parsed):
        if isinstance(parsed, list):
            return {
                "source": "static",
                "static": cls._normalize_static_options(parsed),
                "lookup": "",
            }

        if not isinstance(parsed, dict):
            raise FormBuilderDomainValidationError("options must be a JSON object or array.")

        raw_source = str(parsed.get("source") or "").strip().lower()
        if not raw_source:
            raw_source = "lookup" if parsed.get("lookup") else "static"
        if raw_source not in {"static", "lookup"}:
            raise FormBuilderDomainValidationError("options.source must be static or lookup.")

        lookup_key = str(parsed.get("lookup") or "").strip()
        static_options = cls._normalize_static_options(parsed.get("static") or [])
        return {
            "source": raw_source,
            "static": static_options,
            "lookup": lookup_key,
        }

    @staticmethod
    def _normalize_static_options(raw_items):
        if not isinstance(raw_items, list):
            raise FormBuilderDomainValidationError("options.static must be a list.")

        options = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            value = str(item.get("value") or "").strip()
            if not label:
                continue
            options.append({"value": value or label, "label": label})
        return options

    @staticmethod
    def _static_options_from_text(raw_value):
        lines = [
            line.strip()
            for line in str(raw_value or "").replace("\r", "\n").replace("|", "\n").replace(";", "\n").split("\n")
            if line.strip()
        ]
        options = []
        for line in lines:
            if "=" in line:
                label, value = line.split("=", 1)
                options.append({"label": label.strip(), "value": value.strip()})
                continue
            options.append({"label": line, "value": line})
        return options

    @staticmethod
    def _normalize_rule_expression(value):
        normalized = (value or "").strip()
        if not normalized:
            raise FormBuilderDomainValidationError("expression is required for validation rules.")
        return normalized

    @classmethod
    def _normalize_rule_translations(cls, translations):  # noqa: C901
        normalized_items = []

        if isinstance(translations, dict):
            items = translations.items()
            for language_code, message in items:
                normalized_language_code = str(language_code).strip()
                normalized_message = ("" if message is None else str(message).strip())
                if not normalized_language_code:
                    raise FormBuilderDomainValidationError("language_code is required for rule translations.")
                if not normalized_message:
                    raise FormBuilderDomainValidationError("message is required for rule translations.")
                normalized_items.append(
                    FieldValidationRuleTranslationSection(
                        language_code=normalized_language_code,
                        message=normalized_message,
                    )
                )
        else:
            seen_language_codes = set()
            for translation in translations or ():
                language_code = str((translation.get("language_code") or translation.get("language") or "")).strip()
                message = (translation.get("message") or translation.get("value") or "").strip()
                if not language_code:
                    raise FormBuilderDomainValidationError("language_code is required for rule translations.")
                if not message:
                    raise FormBuilderDomainValidationError("message is required for rule translations.")
                normalized_language_code = language_code.lower()
                if normalized_language_code in seen_language_codes:
                    raise FormBuilderDomainValidationError("each rule must have unique translation per language_code.")
                seen_language_codes.add(normalized_language_code)
                normalized_items.append(
                    FieldValidationRuleTranslationSection(
                        language_code=normalized_language_code,
                        message=message,
                    )
                )

        if not normalized_items:
            raise FormBuilderDomainValidationError("validation rule must have at least one translation.")

        seen_language_codes = set()
        deduped_items = []
        for translation in normalized_items:
            normalized_language_code = translation.language_code.lower()
            if normalized_language_code in seen_language_codes:
                raise FormBuilderDomainValidationError("each rule must have unique translation per language_code.")
            seen_language_codes.add(normalized_language_code)
            deduped_items.append(
                FieldValidationRuleTranslationSection(
                    language_code=normalized_language_code,
                    message=translation.message,
                )
            )

        return tuple(deduped_items)

    @staticmethod
    def _nullable_text(value):
        normalized = (value or "").strip()
        return normalized or None

    @staticmethod
    def _to_int(value):
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _to_decimal(value):
        if value in (None, ""):
            return None
        return Decimal(str(value))

import json
import re

from django.utils.translation import gettext_lazy as _


class SubjectDetailRenderingMixin:
    @classmethod
    def _normalize_control_type(cls, raw_control_type):
        if not raw_control_type:
            return "text"
        normalized_value = str(raw_control_type).strip().lower()
        return cls.supported_control_type_map.get(normalized_value, "unsupported")

    @staticmethod
    def _normalize_control_layout(raw_control_layout):
        normalized_value = str(raw_control_layout or "").strip().lower()
        if normalized_value in {"normal", "card", "table_row"}:
            return normalized_value
        return "normal"

    @staticmethod
    def _normalize_section_layout_type(raw_layout_type):
        normalized_value = str(raw_layout_type or "").strip().lower()
        if normalized_value in {"section", "table"}:
            return normalized_value
        return "section"

    @staticmethod
    def _normalize_schema_boolean(raw_value, *, default):
        if raw_value is None:
            return default
        if isinstance(raw_value, bool):
            return raw_value
        normalized_value = str(raw_value).strip().lower()
        if normalized_value in {"1", "true", "yes", "on"}:
            return True
        if normalized_value in {"0", "false", "no", "off"}:
            return False
        return default

    @classmethod
    def _default_table_layout_schema(cls):
        return {
            "show_table_header": True,
            "response_direction": "horizontal",
            "columns": [
                {
                    "key": "index",
                    "label": "#",
                    "width": "40px",
                    "source": "display_order",
                    "header_class": "subject-form-table-section__head--index",
                    "cell_class": "subject-form-table-row__cell--index",
                },
                {
                    "key": "criterion",
                    "label": _("Criterion"),
                    "width": "",
                    "source": "label",
                    "header_class": "subject-form-table-section__head--criterion",
                    "cell_class": "subject-form-table-row__cell--criterion",
                },
                {
                    "key": "response",
                    "label": _("Response"),
                    "width": "239px",
                    "source": "control",
                    "header_class": "subject-form-table-section__head--response",
                    "cell_class": "subject-form-table-row__cell--response",
                },
            ],
        }

    @classmethod
    def _normalize_table_column_schema(cls, raw_column):
        if not isinstance(raw_column, dict):
            return None

        source = str(raw_column.get("source") or raw_column.get("key") or "").strip().lower()
        source_aliases = {
            "ordinal": "display_order",
            "index": "display_order",
            "#": "display_order",
            "criterion": "label",
            "response": "control",
        }
        normalized_source = source_aliases.get(source, source)
        if normalized_source not in {"display_order", "label", "control", "field_key", "data_type"}:
            return None

        default_schema = {
            "display_order": {
                "key": "index",
                "label": "#",
                "cell_class": "subject-form-table-row__cell--index",
                "header_class": "subject-form-table-section__head--index",
            },
            "label": {
                "key": "criterion",
                "label": _("Criterion"),
                "cell_class": "subject-form-table-row__cell--criterion",
                "header_class": "subject-form-table-section__head--criterion",
            },
            "control": {
                "key": "response",
                "label": _("Response"),
                "cell_class": "subject-form-table-row__cell--response",
                "header_class": "subject-form-table-section__head--response",
            },
            "field_key": {
                "key": "field_key",
                "label": _("Field Key"),
                "cell_class": "subject-form-table-row__cell--field-key",
                "header_class": "subject-form-table-section__head--field-key",
            },
            "data_type": {
                "key": "data_type",
                "label": _("Data Type"),
                "cell_class": "subject-form-table-row__cell--data-type",
                "header_class": "subject-form-table-section__head--data-type",
            },
        }[normalized_source]

        return {
            "key": str(raw_column.get("key") or default_schema["key"]).strip() or default_schema["key"],
            "label": raw_column.get("label") or default_schema["label"],
            "width": str(raw_column.get("width") or "").strip(),
            "source": normalized_source,
            "header_class": (
                str(raw_column.get("header_class") or default_schema["header_class"]).strip()
            ),
            "cell_class": (
                str(raw_column.get("cell_class") or default_schema["cell_class"]).strip()
            ),
        }

    @classmethod
    def _normalize_table_layout_schema(cls, raw_schema):
        default_schema = cls._default_table_layout_schema()
        if not isinstance(raw_schema, dict):
            return default_schema

        raw_columns = raw_schema.get("columns")
        normalized_columns = []
        if isinstance(raw_columns, list):
            for raw_column in raw_columns:
                normalized_column = cls._normalize_table_column_schema(raw_column)
                if normalized_column is not None:
                    normalized_columns.append(normalized_column)
        if not normalized_columns:
            normalized_columns = default_schema["columns"]

        response_direction = str(raw_schema.get("response_direction") or "").strip().lower()
        if response_direction not in {"horizontal", "vertical"}:
            response_direction = default_schema["response_direction"]

        return {
            "show_table_header": cls._normalize_schema_boolean(
                raw_schema.get("show_table_header"),
                default=default_schema["show_table_header"],
            ),
            "response_direction": response_direction,
            "columns": normalized_columns,
        }

    @classmethod
    def _build_table_row_cells(cls, field, columns):
        row_cells = []
        for column in columns:
            source = column.get("source")
            cell_payload = {
                "key": column.get("key"),
                "source": source,
                "cell_class": column.get("cell_class") or "",
            }
            if source == "control":
                row_cells.append(
                    {
                        **cell_payload,
                        "kind": "control",
                    }
                )
                continue

            if source == "display_order":
                value = field.get("display_order")
            elif source == "label":
                value = field.get("label") or field.get("field_key")
            elif source == "field_key":
                value = field.get("field_key")
            elif source == "data_type":
                value = field.get("data_type")
            else:
                value = field.get(source)

            row_cells.append(
                {
                    **cell_payload,
                    "kind": "text",
                    "text": value if value not in (None, "") else "—",
                    "show_required": source == "label" and field.get("is_required"),
                    "helper_text": field.get("helper_text") if source == "label" else "",
                }
            )

        return row_cells

    @classmethod
    def _parse_choice_options(cls, raw_value):  # noqa: C901
        if not raw_value:
            return []

        if isinstance(raw_value, list):
            normalized_options = cls._normalize_choice_option_items(raw_value)
            if normalized_options:
                return normalized_options

        if isinstance(raw_value, str):
            stripped_value = raw_value.strip()
            if stripped_value.startswith("[") and stripped_value.endswith("]"):
                try:
                    loaded_options = json.loads(stripped_value)
                except json.JSONDecodeError:
                    loaded_options = None
                else:
                    normalized_options = cls._normalize_choice_option_items(
                        loaded_options
                    )
                    if normalized_options:
                        return normalized_options

        normalized = str(raw_value).replace("\r", "\n")
        normalized = normalized.replace("|", "\n").replace(";", "\n")
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        options = []

        pair_pattern = re.compile(
            r"([^=]+?)\s*=\s*([^=]+?)(?=\s+[^=]+?\s*=|$)"
        )
        for line in lines:
            if "=" in line:
                matched_pairs = pair_pattern.findall(line)
                if matched_pairs:
                    for label, value in matched_pairs:
                        options.append(
                            {
                                "label": label.strip(),
                                "value": value.strip(),
                            }
                        )
                    continue
                label, value = line.split("=", 1)
                options.append({"label": label.strip(), "value": value.strip()})
                continue

            options.append({"label": line, "value": line})

        return [option for option in options if option["label"]]

    @staticmethod
    def _normalize_choice_option_items(raw_items):
        if not isinstance(raw_items, list):
            return []

        options = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue

            label = str(item.get("label") or "").strip()
            value = str(item.get("value") or "").strip()
            if not label:
                continue
            if not value:
                value = label
            options.append({"value": value, "label": label})

        return options

    @staticmethod
    def _normalize_scalar_field_value(raw_value):
        if raw_value is None:
            return ""
        if isinstance(raw_value, bool):
            return "true" if raw_value else "false"
        return str(raw_value)

    @staticmethod
    def _normalize_multi_value(raw_value):
        if raw_value in (None, ""):
            return []
        if isinstance(raw_value, list):
            return [str(item) for item in raw_value]
        if isinstance(raw_value, tuple):
            return [str(item) for item in raw_value]
        if isinstance(raw_value, str):
            values = [part.strip() for part in raw_value.split(",") if part.strip()]
            if values:
                return values
            stripped_value = raw_value.strip()
            return [stripped_value] if stripped_value else []
        return [str(raw_value)]

    @staticmethod
    def _resolve_field_payload_value(payload_map, field):
        field_key = str(field.get("field_key") or "").strip()
        field_id = field.get("id")
        aliases = []
        if field_key:
            aliases.append(field_key)
        if field_id not in (None, ""):
            aliases.append(f"field_{field_id}")
        for alias in aliases:
            if alias in payload_map:
                return alias, payload_map[alias]
        return field_key, None

    def _build_form_render_sections(self, focused_form_fields, entry_payload_map=None):
        if not focused_form_fields:
            return []
        payload_map = entry_payload_map if isinstance(entry_payload_map, dict) else {}

        sections_by_key = {}
        for field in focused_form_fields:
            section_template = field.get("section_template") or {}
            section_title = (section_template.get("name") or "").strip() or _("General")
            section_order = section_template.get("display_order")
            if section_order is None:
                section_order = 999999
            section_layout_config = section_template.get("layout_config") or {}
            section_layout_type = self._normalize_section_layout_type(
                section_layout_config.get("layout_type")
            )
            table_layout = self._normalize_table_layout_schema(
                section_layout_config.get("custom_layout_schema")
            )

            section_key = (
                section_template.get("id")
                or section_template.get("code")
                or f"general::{section_title}"
            )
            if section_key not in sections_by_key:
                sections_by_key[section_key] = {
                    "id": section_template.get("id"),
                    "code": section_template.get("code"),
                    "code_class": str(section_template.get("code") or "").strip().lower(),
                    "title": section_title,
                    "order": section_order,
                    "layout_type": section_layout_type,
                    "layout_schema": section_layout_config.get("custom_layout_schema") or {},
                    "table_layout": table_layout,
                    "layout_css_class": (
                        section_layout_config.get("custom_css_class") or ""
                    ).strip(),
                    "show_section_header": section_layout_config.get(
                        "show_section_header", True
                    ),
                    "fields": [],
                    "columns": 1,
                }

            ui_config = field.get("ui_config") or {}
            control_type = self._normalize_control_type(ui_config.get("control_type"))
            control_layout = self._normalize_control_layout(ui_config.get("control_layout"))
            options = self._parse_choice_options(ui_config.get("options") or field.get("codelist"))
            placeholder_text = (ui_config.get("text") or "").strip()
            helper_text = (field.get("comments") or "").strip()
            resolved_alias, resolved_value = self._resolve_field_payload_value(payload_map, field)
            selected_values = self._normalize_multi_value(resolved_value)
            normalized_value = self._normalize_scalar_field_value(resolved_value)

            sections_by_key[section_key]["fields"].append(
                {
                    "id": field.get("id"),
                    "field_key": field.get("field_key"),
                    "label": field.get("label") or field.get("field_key"),
                    "data_type": field.get("data_type"),
                    "display_order": field.get("display_order") or 999999,
                    "control_type": control_type,
                    "control_layout": control_layout,
                    "raw_control_type": ui_config.get("control_type"),
                    "placeholder_text": placeholder_text,
                    "helper_text": helper_text,
                    "options": options,
                    "is_required": "required" in (ui_config.get("behavior") or "").lower(),
                    "classes": (ui_config.get("classes") or "").strip(),
                    "range_min": field.get("range_min"),
                    "range_max": field.get("range_max"),
                    "text_min_length": field.get("text_min_length"),
                    "text_max_length": field.get("text_max_length"),
                    "pattern": field.get("pattern"),
                    "pattern_err_msg": field.get("pattern_err_msg"),
                    "value": normalized_value,
                    "is_checked": str(normalized_value).lower() in {"1", "true", "yes", "on"},
                    "selected_values": selected_values,
                    "date_day": self._normalize_scalar_field_value(
                        payload_map.get(f"{resolved_alias}__day")
                    ),
                    "date_month": self._normalize_scalar_field_value(
                        payload_map.get(f"{resolved_alias}__month")
                    ),
                    "date_year": self._normalize_scalar_field_value(
                        payload_map.get(f"{resolved_alias}__year")
                    ),
                    "date_time": self._normalize_scalar_field_value(
                        payload_map.get(f"{resolved_alias}__time")
                    ),
                }
            )

        payload = []
        ordered_sections = sorted(
            sections_by_key.values(),
            key=lambda section: (
                section.get("order", 999999),
                str(section.get("title") or "").lower(),
            ),
        )
        for section in ordered_sections:
            section["fields"] = sorted(
                section["fields"],
                key=lambda field: (
                    field.get("display_order", 999999),
                    str(field.get("label") or "").lower(),
                ),
            )
            field_count = len(section["fields"])
            if field_count <= 1:
                section["columns"] = 1
            elif field_count == 2:
                section["columns"] = 2
            else:
                section["columns"] = 3
            if section.get("layout_type") == "table":
                section["table_layout"] = self._normalize_table_layout_schema(
                    section.get("layout_schema")
                )
                section["fields"] = [
                    {
                        **field,
                        "table_row_cells": self._build_table_row_cells(
                            field,
                            section["table_layout"]["columns"],
                        ),
                    }
                    for field in section["fields"]
                ]
            payload.append(section)
        return payload

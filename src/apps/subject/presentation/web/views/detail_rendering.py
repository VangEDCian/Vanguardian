import json
import re

from django.utils.translation import gettext_lazy as _

from apps.core.form_data_document import REPEAT_COUNTS_EXPORT_META_KEY


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
        if normalized_value in {"section", "table", "repeat_table"}:
            return normalized_value
        if normalized_value in {"repeat_rows", "repeat-row-table", "repeat_row_table"}:
            return "repeat_table"
        return "section"

    @staticmethod
    def _normalize_behavior_payload(raw_behavior):
        if isinstance(raw_behavior, dict):
            source = raw_behavior
        else:
            normalized_behavior = str(raw_behavior or "").strip()
            if not normalized_behavior:
                return {}
            try:
                parsed = json.loads(normalized_behavior)
            except (TypeError, ValueError, json.JSONDecodeError):
                parsed = None
            if not isinstance(parsed, dict):
                return {"required": normalized_behavior}
            source = parsed

        normalized_payload = {}
        for key, value in source.items():
            normalized_key = str(key or "").strip().lower()
            if not normalized_key:
                continue
            normalized_payload[normalized_key] = "" if value is None else str(value).strip()
        return normalized_payload

    @staticmethod
    def _behavior_value(behavior_payload, key):
        if not isinstance(behavior_payload, dict):
            return ""
        return str(behavior_payload.get(key) or "").strip()

    @classmethod
    def _is_required_from_behavior(cls, behavior_payload):
        required_when = cls._behavior_value(behavior_payload, "required_when")
        if required_when:
            return False

        required_flag = cls._behavior_value(behavior_payload, "required")
        if required_flag.lower() in {"1", "true", "yes", "on", "required"}:
            return True

        return required_flag.lower() == "always"

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
    def _default_repeat_table_layout_schema(cls):
        return {
            "show_table_header": True,
            "show_row_number": True,
            "row_number_label": _("STT"),
            "row_number_width": "56px",
        }

    @classmethod
    def _normalize_repeat_table_layout_schema(cls, raw_schema):
        default_schema = cls._default_repeat_table_layout_schema()
        if not isinstance(raw_schema, dict):
            return default_schema

        return {
            "show_table_header": cls._normalize_schema_boolean(
                raw_schema.get("show_table_header"),
                default=default_schema["show_table_header"],
            ),
            "show_row_number": cls._normalize_schema_boolean(
                raw_schema.get("show_row_number"),
                default=default_schema["show_row_number"],
            ),
            "row_number_label": (
                str(raw_schema.get("row_number_label") or default_schema["row_number_label"]).strip()
                or default_schema["row_number_label"]
            ),
            "row_number_width": (
                str(raw_schema.get("row_number_width") or default_schema["row_number_width"]).strip()
                or default_schema["row_number_width"]
            ),
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

        if isinstance(raw_value, dict):
            source = str(raw_value.get("source") or "").strip().lower()
            if source == "static" or raw_value.get("static") is not None:
                normalized_options = cls._normalize_choice_option_items(raw_value.get("static") or [])
                if normalized_options:
                    return normalized_options
            return []

        if isinstance(raw_value, list):
            normalized_options = cls._normalize_choice_option_items(raw_value)
            if normalized_options:
                return normalized_options

        if isinstance(raw_value, str):
            stripped_value = raw_value.strip()
            if stripped_value.startswith(("[", "{")) and stripped_value.endswith(("]", "}")):
                try:
                    loaded_options = json.loads(stripped_value)
                except json.JSONDecodeError:
                    loaded_options = None
                else:
                    if isinstance(loaded_options, dict):
                        loaded_options = loaded_options.get("static") or []
                    normalized_options = cls._normalize_choice_option_items(loaded_options)
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

    @classmethod
    def _normalize_options_config(cls, raw_value):
        if not raw_value:
            return {
                "source": "",
                "static": [],
                "lookup": "",
            }

        parsed = raw_value
        if isinstance(raw_value, str):
            stripped_value = raw_value.strip()
            if stripped_value.startswith("{") and stripped_value.endswith("}"):
                try:
                    parsed = json.loads(stripped_value)
                except json.JSONDecodeError:
                    parsed = {}
            elif stripped_value.startswith("[") and stripped_value.endswith("]"):
                try:
                    parsed = json.loads(stripped_value)
                except json.JSONDecodeError:
                    parsed = []

        if isinstance(parsed, list):
            return {
                "source": "",
                "static": cls._normalize_choice_option_items(parsed),
                "lookup": "",
            }
        if isinstance(parsed, dict):
            source = str(parsed.get("source") or "").strip().lower()
            if source not in {"static", "lookup"}:
                source = ""
            return {
                "source": source,
                "static": cls._normalize_choice_option_items(parsed.get("static") or []),
                "lookup": str(parsed.get("lookup") or "").strip(),
            }
        return {
            "source": "",
            "static": [],
            "lookup": "",
        }

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

    @classmethod
    def _option_label_by_value(cls, *, options_config, options):
        if not cls._has_static_options_source(options_config):
            return {}
        label_by_value = {}
        for option in options or []:
            if not isinstance(option, dict):
                continue
            label = str(option.get("label") or "").strip()
            value = str(option.get("value") or label).strip()
            if value and label:
                label_by_value[value] = label
        return label_by_value

    @classmethod
    def _display_value_for_control(cls, *, raw_value, selected_values, options_config, options):
        label_by_value = cls._option_label_by_value(options_config=options_config, options=options)
        if not label_by_value:
            return cls._normalize_scalar_field_value(raw_value)

        values = selected_values or cls._normalize_multi_value(raw_value)
        labels = [label_by_value.get(str(value), str(value)) for value in values if str(value).strip()]
        if labels:
            return ", ".join(labels)
        return cls._normalize_scalar_field_value(raw_value)

    @staticmethod
    def _has_static_options_source(options_config):
        return bool(
            options_config
            and options_config.get("source") == "static"
            and options_config.get("static")
        )

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

    @staticmethod
    def _repeat_field_key(field_key, repeat_index):
        if repeat_index <= 1:
            return str(field_key or "").strip()
        return f"{str(field_key or '').strip()}__repeat_{repeat_index}"

    @classmethod
    def _repeat_aliases_for_field(cls, field, repeat_index):
        aliases = []
        field_key = str(field.get("field_key") or "").strip()
        if field_key:
            aliases.append(cls._repeat_field_key(field_key, repeat_index))
        field_id = field.get("id")
        if field_id not in (None, ""):
            aliases.append(cls._repeat_field_key(f"field_{field_id}", repeat_index))
        return aliases

    @classmethod
    def _resolve_repeat_payload_value(cls, payload_map, field, repeat_index):
        if repeat_index <= 1:
            return cls._resolve_field_payload_value(payload_map, field)
        aliases = cls._repeat_aliases_for_field(field, repeat_index)
        for alias in aliases:
            if alias in payload_map:
                return alias, payload_map[alias]
        return aliases[0] if aliases else "", None

    @classmethod
    def _resolve_repeat_count(cls, section_fields, payload_map, max_repeats, section_code=None):
        repeat_count = cls._repeat_count_from_payload_meta(payload_map, section_code)
        field_keys = [str(field.get("field_key") or "").strip() for field in section_fields]
        field_keys.extend(
            f"field_{field.get('id')}"
            for field in section_fields
            if field.get("id") not in (None, "")
        )
        escaped_keys = [re.escape(field_key) for field_key in field_keys if field_key]
        if escaped_keys:
            repeat_pattern = re.compile(rf"^(?:{'|'.join(escaped_keys)})__repeat_(\d+)(?:__(?:day|month|year|time))?$")
            for payload_key in payload_map:
                matched = repeat_pattern.match(str(payload_key))
                if not matched:
                    continue
                repeat_count = max(repeat_count, int(matched.group(1)))
        if max_repeats is not None:
            try:
                repeat_count = min(repeat_count, max(1, int(max_repeats)))
            except (TypeError, ValueError):
                pass
        return repeat_count

    @staticmethod
    def _repeat_count_from_payload_meta(payload_map, section_code):
        if not isinstance(payload_map, dict):
            return 1
        meta = payload_map.get(REPEAT_COUNTS_EXPORT_META_KEY)
        if not isinstance(meta, dict):
            return 1
        normalized_section_code = str(section_code or "").strip()
        if not normalized_section_code:
            return 1
        try:
            return max(1, int(meta.get(normalized_section_code) or 1))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _can_add_repeat_instance(current_repeats, max_repeats):
        if max_repeats is None:
            return True
        try:
            return int(current_repeats) < int(max_repeats)
        except (TypeError, ValueError):
            return False

    def _field_for_repeat_instance(self, field, repeat_index, payload_map):
        if repeat_index <= 1:
            return field

        repeated_field = {
            key: value
            for key, value in field.items()
            if key
            not in {
                "active_query_id",
                "active_query_is_answered",
                "query_thread_badge_count",
                "query_messages",
            }
        }
        base_field_key = str(field.get("field_key") or "").strip()
        repeated_field_key = self._repeat_field_key(base_field_key, repeat_index)
        resolved_alias, resolved_value = self._resolve_repeat_payload_value(payload_map, field, repeat_index)
        selected_values = self._normalize_multi_value(resolved_value)
        normalized_value = self._normalize_scalar_field_value(resolved_value)
        display_value = self._display_value_for_control(
            raw_value=resolved_value,
            selected_values=selected_values,
            options_config=field.get("options_config") or {},
            options=field.get("options") or [],
        )
        date_day, date_month, date_year, date_time = self._extract_composite_date_parts(normalized_value)
        date_day = date_day or self._normalize_scalar_field_value(payload_map.get(f"{resolved_alias}__day"))
        date_month = date_month or self._normalize_scalar_field_value(payload_map.get(f"{resolved_alias}__month"))
        date_year = date_year or self._normalize_scalar_field_value(payload_map.get(f"{resolved_alias}__year"))
        date_time = date_time or self._normalize_scalar_field_value(payload_map.get(f"{resolved_alias}__time"))

        repeated_field.update(
            {
                "field_key": repeated_field_key,
                "repeat_base_field_key": base_field_key,
                "repeat_instance_index": repeat_index,
                "value": normalized_value,
                "display_value": display_value,
                "is_checked": str(normalized_value).lower() in {"1", "true", "yes", "on"},
                "selected_values": selected_values,
                "date_day": date_day,
                "date_month": date_month,
                "date_year": date_year,
                "date_time": date_time,
            }
        )
        return repeated_field

    @staticmethod
    def _extract_composite_date_parts(raw_value):
        normalized = str(raw_value or "").strip()
        if not normalized:
            return "", "", "", ""
        matched = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::\d{2})?)?$", normalized)
        if not matched:
            return "", "", "", ""
        year = str(int(matched.group(1)))
        month = str(int(matched.group(2)))
        day = str(int(matched.group(3)))
        hour = matched.group(4) or ""
        minute = matched.group(5) or ""
        time_value = f"{hour}:{minute}" if hour and minute else ""
        return day, month, year, time_value

    def _build_form_render_sections(
        self,
        focused_form_fields,
        entry_payload_map=None,
        field_query_state_by_id=None,
    ):
        if not focused_form_fields:
            return []
        payload_map = entry_payload_map if isinstance(entry_payload_map, dict) else {}
        query_state_by_id = field_query_state_by_id if isinstance(field_query_state_by_id, dict) else {}

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
            repeat_table_layout = self._normalize_repeat_table_layout_schema(
                section_layout_config.get("custom_layout_schema")
            )

            section_key = (
                section_template.get("id")
                or section_template.get("code")
                or f"general::{section_title}"
            )
            if section_key not in sections_by_key:
                is_repeatable = bool(section_template.get("is_repeatable"))
                max_repeats = section_template.get("max_repeats")
                sections_by_key[section_key] = {
                    "id": section_template.get("id"),
                    "code": section_template.get("code"),
                    "code_class": str(section_template.get("code") or "").strip().lower(),
                    "title": section_title,
                    "order": section_order,
                    "layout_type": section_layout_type,
                    "layout_schema": section_layout_config.get("custom_layout_schema") or {},
                    "table_layout": table_layout,
                    "repeat_table_layout": repeat_table_layout,
                    "layout_css_class": (
                        section_layout_config.get("custom_css_class") or ""
                    ).strip(),
                    "show_section_header": section_layout_config.get(
                        "show_section_header", True
                    ),
                    "is_repeatable": is_repeatable,
                    "min_repeats": section_template.get("min_repeats") or 0,
                    "max_repeats": max_repeats,
                    "fields": [],
                    "columns": 1,
                }

            ui_config = field.get("ui_config") or {}
            behavior_payload = self._normalize_behavior_payload(ui_config.get("behavior"))
            control_type = self._normalize_control_type(ui_config.get("control_type"))
            control_layout = self._normalize_control_layout(ui_config.get("control_layout"))
            options_config = self._normalize_options_config(ui_config.get("options"))
            raw_options = options_config["static"] if options_config["source"] == "static" else ui_config.get("options")
            options = self._parse_choice_options(raw_options or field.get("codelist"))
            placeholder_text = (ui_config.get("text") or "").strip()
            helper_text = (field.get("comments") or "").strip()
            resolved_alias, resolved_value = self._resolve_field_payload_value(payload_map, field)
            selected_values = self._normalize_multi_value(resolved_value)
            normalized_value = self._normalize_scalar_field_value(resolved_value)
            display_value = self._display_value_for_control(
                raw_value=resolved_value,
                selected_values=selected_values,
                options_config=options_config,
                options=options,
            )
            date_day, date_month, date_year, date_time = self._extract_composite_date_parts(
                normalized_value
            )
            date_day = date_day or self._normalize_scalar_field_value(
                payload_map.get(f"{resolved_alias}__day")
            )
            date_month = date_month or self._normalize_scalar_field_value(
                payload_map.get(f"{resolved_alias}__month")
            )
            date_year = date_year or self._normalize_scalar_field_value(
                payload_map.get(f"{resolved_alias}__year")
            )
            date_time = date_time or self._normalize_scalar_field_value(
                payload_map.get(f"{resolved_alias}__time")
            )

            try:
                query_state_key = int(field.get("id"))
            except (TypeError, ValueError):
                query_state_key = field.get("id")

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
                    "options_config": options_config,
                    "lookup_key": options_config["lookup"] if options_config["source"] == "lookup" else "",
                    "is_required": self._is_required_from_behavior(behavior_payload),
                    "behavior_visible_when": self._behavior_value(behavior_payload, "visible_when"),
                    "behavior_readonly_when": self._behavior_value(behavior_payload, "readonly_when"),
                    "behavior_required_when": self._behavior_value(behavior_payload, "required_when"),
                    "behavior_default_value": self._behavior_value(behavior_payload, "default_value"),
                    "behavior_default_value_expr": self._behavior_value(
                        behavior_payload,
                        "default_value_expr",
                    ),
                    "classes": (ui_config.get("classes") or "").strip(),
                    "style": (ui_config.get("style") or "").strip(),
                    "range_min": field.get("range_min"),
                    "range_max": field.get("range_max"),
                    "text_min_length": field.get("text_min_length"),
                    "text_max_length": field.get("text_max_length"),
                    "pattern": field.get("pattern"),
                    "pattern_err_msg": field.get("pattern_err_msg"),
                    "value": normalized_value,
                    "display_value": display_value,
                    "is_checked": str(normalized_value).lower() in {"1", "true", "yes", "on"},
                    "selected_values": selected_values,
                    "date_day": date_day,
                    "date_month": date_month,
                    "date_year": date_year,
                    "date_time": date_time,
                    **query_state_by_id.get(query_state_key, {}),
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
            repeat_count = (
                self._resolve_repeat_count(
                    section["fields"],
                    payload_map,
                    section.get("max_repeats"),
                    section_code=section.get("code"),
                )
                if section.get("is_repeatable")
                else 1
            )
            field_count = len(section["fields"])
            if field_count <= 1:
                section["columns"] = 1
            elif field_count == 2:
                section["columns"] = 2
            else:
                section["columns"] = 3

            if section.get("layout_type") == "repeat_table":
                repeated_rows = []
                for repeat_index in range(1, repeat_count + 1):
                    repeated_rows.append(
                        {
                            "repeat_instance_index": repeat_index,
                            "fields": [
                                self._field_for_repeat_instance(field, repeat_index, payload_map)
                                for field in section["fields"]
                            ],
                        }
                    )
                payload.append(
                    {
                        **section,
                        "repeat_table_rows": repeated_rows,
                        "repeat_instance_index": 1,
                        "current_repeats": repeat_count,
                        "can_add_repeat": (
                            bool(section.get("is_repeatable"))
                            and self._can_add_repeat_instance(
                                repeat_count,
                                section.get("max_repeats"),
                            )
                        ),
                    }
                )
                continue

            for repeat_index in range(1, repeat_count + 1):
                repeated_section = {
                    **section,
                    "fields": [
                        self._field_for_repeat_instance(field, repeat_index, payload_map)
                        for field in section["fields"]
                    ],
                    "repeat_instance_index": repeat_index,
                    "current_repeats": repeat_count,
                    "can_add_repeat": (
                        bool(section.get("is_repeatable"))
                        and repeat_index == repeat_count
                        and self._can_add_repeat_instance(repeat_count, section.get("max_repeats"))
                    ),
                }
                if repeated_section.get("layout_type") == "table":
                    repeated_section["table_layout"] = self._normalize_table_layout_schema(
                        repeated_section.get("layout_schema")
                    )
                    repeated_section["fields"] = [
                        {
                            **field,
                            "table_row_cells": self._build_table_row_cells(
                                field,
                                repeated_section["table_layout"]["columns"],
                            ),
                        }
                        for field in repeated_section["fields"]
                    ]
                payload.append(repeated_section)
        return payload

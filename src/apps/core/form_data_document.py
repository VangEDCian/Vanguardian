import copy
import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

FORM_DATA_FORMAT = "edc.form_data.v1"
LEGACY_UNMAPPED_SECTION_CODE = "_LEGACY_UNMAPPED_FIELDS"
REPEAT_COUNTS_EXPORT_META_KEY = "_repeat_counts_by_section_code"
LEGACY_CONVERSION_WARNINGS_META_KEY = "legacy_conversion_warnings"

_DATE_PART_KEY_RE = re.compile(r"^(?P<base>.+)__(?P<part>day|month|year|time)$")
_REPEAT_KEY_RE = re.compile(r"^(?P<base>.+)__repeat_(?P<repeat_index>\d+)$")
_SUSPICIOUS_INDEXED_KEY_RE = re.compile(r"^.+_\d+$")

logger = logging.getLogger(__name__)


class FormDataNormalizationError(ValueError):
    def __init__(self, message: str, *, unmapped_fields: tuple[str, ...] = ()):
        super().__init__(message)
        self.unmapped_fields = unmapped_fields


@dataclass(frozen=True)
class FieldTemplateSnapshot:
    field_key: str
    section_code: str
    data_type: str | None = None
    display_order: int | None = None


@dataclass(frozen=True)
class SectionTemplateSnapshot:
    section_code: str
    is_repeatable: bool
    display_order: int | None = None
    fields: list[FieldTemplateSnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class FormTemplateSnapshot:
    form_code: str
    form_version: str
    sections: list[SectionTemplateSnapshot]

    def field_by_key(self) -> dict[str, FieldTemplateSnapshot]:
        out: dict[str, FieldTemplateSnapshot] = {}
        for section in self.sections:
            for field_snapshot in section.fields:
                field_key = str(field_snapshot.field_key or "").strip()
                if field_key:
                    out[field_key] = field_snapshot
        return out

    def section_by_code(self) -> dict[str, SectionTemplateSnapshot]:
        return {
            str(section.section_code or "").strip(): section
            for section in self.sections
            if str(section.section_code or "").strip()
        }


@dataclass(frozen=True)
class FormFieldValueRef:
    section_code: str
    section_kind: str
    row_key: str | None
    row_no: int | None
    field_key: str
    value: Any
    path: str


def is_canonical_form_data(data: dict) -> bool:
    return isinstance(data, dict) and data.get("format") == FORM_DATA_FORMAT


def build_field_path(section_code, field_key, row_key=None) -> str:
    section = str(section_code or "").strip()
    field_name = str(field_key or "").strip()
    if row_key:
        return f"groups.{section}.rows[{row_key}].items.{field_name}"
    return f"groups.{section}.items.{field_name}"


def normalize_form_data(
    raw_data: dict | None,
    *,
    template_snapshot: FormTemplateSnapshot | None = None,
    form_code: str | None = None,
    form_version: str | None = None,
    entry_version: str | int | None = None,
    include_metadata: bool = False,
    strict: bool = False,
) -> dict:
    parsed = _coerce_dict(raw_data)
    if not parsed:
        return _empty_document(
            template_snapshot=template_snapshot,
            form_code=form_code,
            form_version=form_version,
            entry_version=entry_version,
            include_metadata=include_metadata,
        )
    if is_canonical_form_data(parsed):
        return _normalize_canonical_document(
            parsed,
            template_snapshot=template_snapshot,
            form_code=form_code,
            form_version=form_version,
            entry_version=entry_version,
            include_metadata=include_metadata,
        )
    return _legacy_flat_to_canonical(
        parsed,
        template_snapshot=template_snapshot,
        form_code=form_code,
        form_version=form_version,
        entry_version=entry_version,
        include_metadata=include_metadata,
        strict=strict,
    )


def get_field_value(
    doc: dict,
    *,
    section_code: str,
    field_key: str,
    row_key: str | None = None,
    row_no: int | None = None,
    default=None,
):
    normalized_doc = normalize_form_data(doc)
    group = normalized_doc.get("groups", {}).get(str(section_code or "").strip())
    if not isinstance(group, dict):
        return default
    if group.get("kind") == "repeatable":
        row = _find_repeatable_row(group.get("rows"), row_key=row_key, row_no=row_no)
        if not row:
            return default
        items = row.get("items") if isinstance(row, dict) else {}
        return items.get(field_key, default) if isinstance(items, dict) else default
    items = group.get("items")
    return items.get(field_key, default) if isinstance(items, dict) else default


def set_field_value(
    doc: dict,
    *,
    section_code: str,
    field_key: str,
    value,
    row_key: str | None = None,
    row_no: int | None = None,
) -> dict:
    out = normalize_form_data(doc)
    groups = out.setdefault("groups", {})
    section = str(section_code or "").strip()
    is_repeatable = bool(row_key or row_no)
    if is_repeatable:
        group = groups.setdefault(section, {"kind": "repeatable", "rows": []})
        group["kind"] = "repeatable"
        rows = group.setdefault("rows", [])
        row = _find_repeatable_row(rows, row_key=row_key, row_no=row_no)
        if row is None:
            resolved_row_no = int(row_no or len(rows) + 1)
            row = {
                "row_key": str(row_key or _row_key_for_no(resolved_row_no)),
                "row_no": resolved_row_no,
                "items": {},
            }
            rows.append(row)
        row.setdefault("items", {})[str(field_key or "").strip()] = value
        return out
    group = groups.setdefault(section, {"kind": "single", "items": {}})
    group["kind"] = "single"
    group.setdefault("items", {})[str(field_key or "").strip()] = value
    return out


def iter_field_values(doc: dict) -> Iterator[FormFieldValueRef]:
    normalized_doc = normalize_form_data(doc)
    groups = normalized_doc.get("groups")
    if not isinstance(groups, dict):
        return
    for section_code, group in groups.items():
        if not isinstance(group, dict):
            continue
        kind = str(group.get("kind") or "single").strip() or "single"
        if kind == "repeatable":
            rows = group.get("rows") if isinstance(group.get("rows"), list) else []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                items = row.get("items") if isinstance(row.get("items"), dict) else {}
                row_key = str(row.get("row_key") or "").strip() or None
                row_no = _coerce_int(row.get("row_no"))
                for field_key, value in items.items():
                    yield FormFieldValueRef(
                        section_code=str(section_code),
                        section_kind="repeatable",
                        row_key=row_key,
                        row_no=row_no,
                        field_key=str(field_key),
                        value=value,
                        path=build_field_path(section_code, field_key, row_key=row_key),
                    )
            continue
        items = group.get("items") if isinstance(group.get("items"), dict) else {}
        for field_key, value in items.items():
            yield FormFieldValueRef(
                section_code=str(section_code),
                section_kind="single",
                row_key=None,
                row_no=None,
                field_key=str(field_key),
                value=value,
                path=build_field_path(section_code, field_key),
            )


def flatten_form_data_for_export(doc: dict, *, repeat_strategy: str = "row_suffix") -> dict:
    if not isinstance(doc, dict):
        return {}
    if not is_canonical_form_data(doc):
        return {str(key): value for key, value in doc.items() if not str(key).startswith("_")}
    out: dict[str, Any] = {}
    for ref in iter_field_values(doc):
        if ref.section_code == LEGACY_UNMAPPED_SECTION_CODE:
            out[ref.field_key] = ref.value
        elif ref.section_kind == "repeatable":
            out[_repeat_export_key(ref, repeat_strategy=repeat_strategy)] = ref.value
        else:
            out[ref.field_key] = ref.value
    return out


def extract_repeat_counts_by_section(doc: dict) -> dict[str, int]:
    if not isinstance(doc, dict):
        return {}
    normalized_doc = normalize_form_data(doc)
    groups = normalized_doc.get("groups")
    if not isinstance(groups, dict):
        return {}
    counts: dict[str, int] = {}
    for section_code, group in groups.items():
        if not isinstance(group, dict) or group.get("kind") != "repeatable":
            continue
        rows = group.get("rows") if isinstance(group.get("rows"), list) else []
        repeat_count = 0
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            items = row.get("items") if isinstance(row.get("items"), dict) else {}
            if not any(_has_meaningful_form_value(value) for value in items.values()):
                continue
            repeat_count = max(repeat_count, _coerce_int(row.get("row_no")) or index)
        if repeat_count > 0:
            counts[str(section_code)] = repeat_count
    return counts


def prune_empty_form_data_groups(doc: dict) -> dict:
    normalized_doc = normalize_form_data(doc)
    groups = normalized_doc.get("groups")
    if not isinstance(groups, dict):
        normalized_doc["groups"] = {}
        return normalized_doc

    for section_code, group in list(groups.items()):
        if not isinstance(group, dict):
            groups.pop(section_code, None)
            continue
        if group.get("kind") == "repeatable":
            rows = group.get("rows") if isinstance(group.get("rows"), list) else []
            non_empty_rows = [
                row
                for row in rows
                if isinstance(row, dict)
                and any(
                    _has_meaningful_form_value(value)
                    for value in (row.get("items") if isinstance(row.get("items"), dict) else {}).values()
                )
            ]
            if non_empty_rows:
                group["rows"] = non_empty_rows
                continue
            groups.pop(section_code, None)
            continue

        items = group.get("items") if isinstance(group.get("items"), dict) else {}
        if any(_has_meaningful_form_value(value) for value in items.values()):
            continue
        groups.pop(section_code, None)
    return normalized_doc


def _has_meaningful_form_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return any(_has_meaningful_form_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_meaningful_form_value(item) for item in value.values())
    return True


def _coerce_dict(raw_data) -> dict:
    if raw_data is None:
        return {}
    if isinstance(raw_data, dict):
        return copy.deepcopy(raw_data)
    if isinstance(raw_data, str):
        try:
            parsed = json.loads(raw_data or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _empty_document(
    *,
    template_snapshot: FormTemplateSnapshot | None,
    form_code: str | None,
    form_version: str | None,
    entry_version: str | int | None,
    include_metadata: bool,
) -> dict:
    doc = {
        "format": FORM_DATA_FORMAT,
        "groups": {},
    }
    if include_metadata:
        doc["form_code"] = str(form_code or (template_snapshot.form_code if template_snapshot else "") or "")
        doc["form_version"] = str(form_version or (template_snapshot.form_version if template_snapshot else "") or "")
        doc["entry_version"] = str(entry_version or "")
    _strip_legacy_conversion_warnings(doc)
    return doc


def _normalize_canonical_document(
    raw_doc: dict,
    *,
    template_snapshot: FormTemplateSnapshot | None,
    form_code: str | None,
    form_version: str | None,
    entry_version: str | int | None,
    include_metadata: bool,
) -> dict:
    doc = copy.deepcopy(raw_doc)
    doc["format"] = FORM_DATA_FORMAT
    if include_metadata:
        doc["form_code"] = str(
            doc.get("form_code") or form_code or (template_snapshot.form_code if template_snapshot else "") or ""
        )
        doc["form_version"] = str(
            doc.get("form_version")
            or form_version
            or (template_snapshot.form_version if template_snapshot else "")
            or ""
        )
        doc["entry_version"] = str(doc.get("entry_version") or entry_version or "")
    else:
        doc.pop("form_code", None)
        doc.pop("form_version", None)
        doc.pop("entry_version", None)
    if not isinstance(doc.get("groups"), dict):
        doc["groups"] = {}
    for section_code, group in list(doc["groups"].items()):
        if not isinstance(group, dict):
            doc["groups"].pop(section_code, None)
            continue
        kind = "repeatable" if group.get("kind") == "repeatable" else "single"
        group["kind"] = kind
        if kind == "repeatable":
            rows = group.get("rows") if isinstance(group.get("rows"), list) else []
            normalized_rows = []
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    continue
                row_no = _coerce_int(row.get("row_no")) or index
                normalized_rows.append(
                    {
                        "row_key": str(row.get("row_key") or _row_key_for_no(row_no)),
                        "row_no": row_no,
                        "items": row.get("items") if isinstance(row.get("items"), dict) else {},
                    }
                )
            group["rows"] = normalized_rows
            group.pop("items", None)
        else:
            group["items"] = group.get("items") if isinstance(group.get("items"), dict) else {}
            group.pop("rows", None)
    _strip_legacy_conversion_warnings(doc)
    return doc


def _legacy_flat_to_canonical(
    raw_data: dict,
    *,
    template_snapshot: FormTemplateSnapshot | None,
    form_code: str | None,
    form_version: str | None,
    entry_version: str | int | None,
    include_metadata: bool,
    strict: bool,
) -> dict:
    doc = _empty_document(
        template_snapshot=template_snapshot,
        form_code=form_code,
        form_version=form_version,
        entry_version=entry_version,
        include_metadata=include_metadata,
    )
    if template_snapshot is None:
        if strict:
            raise FormDataNormalizationError("Template snapshot is required to convert legacy form data.")
        fields = {str(key): value for key, value in raw_data.items() if not str(key).startswith("_")}
        if fields:
            logger.warning("Legacy form data read without template snapshot; storing fields as unmapped.")
            doc["groups"][LEGACY_UNMAPPED_SECTION_CODE] = {"kind": "single", "items": fields}
        return doc

    field_by_key = template_snapshot.field_by_key()
    section_by_code = template_snapshot.section_by_code()
    values, warnings = _expand_legacy_flat_values(raw_data, known_field_keys=set(field_by_key))
    unmapped_fields: list[str] = []
    for raw_key, raw_value in values.items():
        if str(raw_key).startswith("_"):
            continue
        base_key, repeat_index = _split_repeat_key(raw_key)
        field_snapshot = field_by_key.get(base_key)
        if field_snapshot is None:
            unmapped_fields.append(str(raw_key))
            continue
        section = section_by_code.get(field_snapshot.section_code)
        if section is None:
            unmapped_fields.append(str(raw_key))
            continue
        if section.is_repeatable:
            row_no = repeat_index or 1
            doc = set_field_value(
                doc,
                section_code=section.section_code,
                field_key=field_snapshot.field_key,
                value=raw_value,
                row_no=row_no,
                row_key=_row_key_for_no(row_no),
            )
        else:
            doc = set_field_value(
                doc,
                section_code=section.section_code,
                field_key=field_snapshot.field_key,
                value=raw_value,
            )

    if unmapped_fields:
        unmapped = tuple(sorted(set(unmapped_fields)))
        if strict:
            raise FormDataNormalizationError("Legacy form data contains fields not found in template.", unmapped_fields=unmapped)
        logger.warning("Legacy form data contains unmapped fields: %s", ", ".join(unmapped))
        doc["groups"][LEGACY_UNMAPPED_SECTION_CODE] = {
            "kind": "single",
            "items": {key: raw_data.get(key) for key in unmapped if key in raw_data},
        }
    if warnings:
        logger.warning("Legacy form data conversion warnings: %s", ", ".join(sorted(set(warnings))))
    return doc


def _expand_legacy_flat_values(
    raw_data: dict,
    *,
    known_field_keys: set[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    values: dict[str, Any] = {}
    date_parts: dict[str, dict[str, str]] = {}
    warnings: list[str] = []
    known_fields = known_field_keys or set()
    for raw_key, raw_value in raw_data.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        if isinstance(raw_value, list) and raw_value and all(isinstance(item, dict) for item in raw_value):
            warnings.append(f"list-object legacy value detected at {key}")
        if _SUSPICIOUS_INDEXED_KEY_RE.match(key) and not _REPEAT_KEY_RE.match(key) and key not in known_fields:
            warnings.append(f"suspicious indexed legacy key detected at {key}")
        date_match = _DATE_PART_KEY_RE.match(key)
        if date_match:
            date_parts.setdefault(date_match.group("base"), {})[date_match.group("part")] = str(raw_value or "").strip()
            continue
        values[key] = raw_value
    for base_key, parts in date_parts.items():
        if base_key in values:
            continue
        year = parts.get("year")
        month = parts.get("month")
        day = parts.get("day")
        if year and month and day:
            values[base_key] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        elif "time" in parts:
            values[base_key] = parts["time"]
        else:
            for part, value in parts.items():
                values[f"{base_key}__{part}"] = value
    return values, warnings


def _strip_legacy_conversion_warnings(doc: dict) -> None:
    meta = doc.get("_meta")
    if not isinstance(meta, dict):
        return
    meta.pop(LEGACY_CONVERSION_WARNINGS_META_KEY, None)
    if not meta:
        doc.pop("_meta", None)


def _split_repeat_key(raw_key: str) -> tuple[str, int | None]:
    key = str(raw_key or "").strip()
    repeat_match = _REPEAT_KEY_RE.match(key)
    if not repeat_match:
        return key, None
    return repeat_match.group("base"), int(repeat_match.group("repeat_index"))


def _find_repeatable_row(rows, *, row_key: str | None, row_no: int | None) -> dict | None:
    if not isinstance(rows, list):
        return None
    normalized_row_key = str(row_key or "").strip()
    normalized_row_no = _coerce_int(row_no)
    for row in rows:
        if not isinstance(row, dict):
            continue
        if normalized_row_key and str(row.get("row_key") or "").strip() == normalized_row_key:
            return row
        if normalized_row_no is not None and _coerce_int(row.get("row_no")) == normalized_row_no:
            return row
    if not normalized_row_key and normalized_row_no is None and rows:
        return rows[0] if isinstance(rows[0], dict) else None
    return None


def _repeat_export_key(ref: FormFieldValueRef, *, repeat_strategy: str) -> str:
    row_no = ref.row_no or 1
    if repeat_strategy == "legacy_repeat_suffix":
        if row_no <= 1:
            return ref.field_key
        return f"{ref.field_key}__repeat_{row_no}"
    if repeat_strategy == "underscore":
        return f"{ref.section_code}_{row_no}_{ref.field_key}"
    return f"{ref.section_code}[{row_no}].{ref.field_key}"


def _row_key_for_no(row_no: int) -> str:
    return f"row_{int(row_no):03d}"


def _coerce_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "FORM_DATA_FORMAT",
    "LEGACY_UNMAPPED_SECTION_CODE",
    "FieldTemplateSnapshot",
    "FormDataNormalizationError",
    "FormFieldValueRef",
    "FormTemplateSnapshot",
    "REPEAT_COUNTS_EXPORT_META_KEY",
    "SectionTemplateSnapshot",
    "build_field_path",
    "extract_repeat_counts_by_section",
    "flatten_form_data_for_export",
    "get_field_value",
    "is_canonical_form_data",
    "iter_field_values",
    "normalize_form_data",
    "prune_empty_form_data_groups",
    "set_field_value",
]

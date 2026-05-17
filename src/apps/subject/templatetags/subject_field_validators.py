from decimal import Decimal, InvalidOperation

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


def _normalize_decimal(raw_value):
    if raw_value in (None, ""):
        return ""
    try:
        return format(Decimal(str(raw_value)), "f")
    except (InvalidOperation, ValueError, TypeError):
        return ""


def _build_html_attrs(attrs):
    chunks = []
    for key, value in attrs.items():
        if value in (None, "", False):
            continue
        if value is True:
            chunks.append(f" {escape(key)}")
            continue
        chunks.append(f' {escape(key)}="{escape(value)}"')
    return mark_safe("".join(chunks))


@register.simple_tag
def subject_text_validator_attrs(field):
    attrs = {
        "data-validator-type": "text",
        "required": bool(field.get("is_required")),
        "minlength": field.get("text_min_length"),
        "maxlength": field.get("text_max_length"),
        "pattern": field.get("pattern") or "",
        "data-validation-message": field.get("pattern_err_msg") or "",
        "data-field-label": field.get("label") or field.get("field_key") or "",
    }
    return _build_html_attrs(attrs)


@register.simple_tag
def subject_number_validator_attrs(field):
    normalized_min = _normalize_decimal(field.get("range_min"))
    normalized_max = _normalize_decimal(field.get("range_max"))
    attrs = {
        "data-validator-type": "number",
        "required": bool(field.get("is_required")),
        "min": normalized_min,
        "max": normalized_max,
        "data-range-min": normalized_min,
        "data-range-max": normalized_max,
        "data-field-label": field.get("label") or field.get("field_key") or "",
    }
    return _build_html_attrs(attrs)


@register.simple_tag
def subject_date_validator_attrs(field):
    attrs = {
        "data-validator-type": "date",
        "required": bool(field.get("is_required")),
        "data-field-label": field.get("label") or field.get("field_key") or "",
    }
    return _build_html_attrs(attrs)

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template
from django.utils.translation import get_language

register = template.Library()


def _to_int(raw_value):
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_raw_to_date_parts(raw_value):
    if isinstance(raw_value, dict):
        day = _to_int(raw_value.get("__day"))
        month = _to_int(raw_value.get("__month"))
        year = _to_int(raw_value.get("__year"))
        time_text = str(raw_value.get("__time") or "").strip()
        return day, month, year, time_text
    text = str(raw_value or "").strip()
    if not text:
        return None, None, None, ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.day, parsed.month, parsed.year, parsed.strftime("%H:%M")
    except ValueError:
        return None, None, None, ""


def _is_vi_language(language_code: str) -> bool:
    normalized = str(language_code or get_language() or "").strip().lower()
    return normalized.startswith("vi")


def _format_date(day, month, year, *, is_vi: bool) -> str:
    if not (day and month and year):
        return ""
    if is_vi:
        return f"{day:02d}/{month:02d}/{year:04d}"
    return f"{month:02d}/{day:02d}/{year:04d}"


def _to_decimal_text(raw_value, precision_raw) -> str:
    text = str(raw_value or "").strip()
    if not text:
        return ""
    normalized = text.replace(",", ".")
    try:
        decimal_value = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return ""
    try:
        precision = int(precision_raw)
    except (TypeError, ValueError):
        return text
    if precision < 0:
        precision = 0
    quantize_unit = Decimal("1").scaleb(-precision) if precision > 0 else Decimal("1")
    rounded = decimal_value.quantize(quantize_unit, rounding=ROUND_HALF_UP)
    formatted = f"{rounded:.{precision}f}" if precision > 0 else f"{rounded:.0f}"
    return formatted.replace(".", ",")


def _to_time_text(raw_value) -> str:
    if isinstance(raw_value, dict):
        time_text = str(raw_value.get("__time") or "").strip()
        if time_text:
            return time_text[:5]
    text = str(raw_value or "").strip()
    if not text:
        return ""
    if len(text) >= 5 and text[2] == ":":
        return text[:5]
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%H:%M")
    except ValueError:
        return ""


@register.simple_tag
def subject_field_review_display_value(row, language_code="en"):
    if not isinstance(row, dict):
        return str(row or "")
    data_type = str(row.get("data_type") or "").strip().upper()
    raw_value = row.get("raw_value")
    base_display = str(row.get("display_value") or "").strip()
    unit = str(row.get("unit") or "").strip()
    precision = row.get("precision")
    is_vi = _is_vi_language(language_code)

    display = base_display
    day, month, year, time_text = _normalize_raw_to_date_parts(raw_value)
    if data_type == "DATE":
        normalized = _format_date(day, month, year, is_vi=is_vi)
        if normalized:
            display = normalized
    elif data_type == "DATETIME":
        normalized_date = _format_date(day, month, year, is_vi=is_vi)
        if normalized_date:
            display = f"{normalized_date} {time_text}".strip() if time_text else normalized_date
    elif data_type == "DECIMAL":
        normalized_decimal = _to_decimal_text(raw_value, precision)
        if normalized_decimal:
            display = normalized_decimal
    elif data_type == "TIME":
        normalized_time = _to_time_text(raw_value)
        if normalized_time:
            display = normalized_time

    if unit and display and display != "—":
        return f"{display} {unit}"
    return display

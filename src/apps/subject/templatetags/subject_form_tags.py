import re

from django import template
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.crf.models import CrfFieldControlTypeChoices

register = template.Library()


_CONTROL_TEMPLATE_MAP = {
    CrfFieldControlTypeChoices.TEXT: "subject/components/controls/_text_control.html",
    CrfFieldControlTypeChoices.TEXTAREA: "subject/components/controls/_textarea_control.html",
    CrfFieldControlTypeChoices.NUMBER: "subject/components/controls/_number_control.html",
    CrfFieldControlTypeChoices.SELECT: "subject/components/controls/_select_control.html",
    CrfFieldControlTypeChoices.SELECT2: "subject/components/controls/_select2_control.html",
    CrfFieldControlTypeChoices.RADIO: "subject/components/controls/_radio_control.html",
    CrfFieldControlTypeChoices.CHECKBOX: "subject/components/controls/_checkbox_control.html",
    CrfFieldControlTypeChoices.MULTI_SELECT: "subject/components/controls/_multi_select_control.html",
    CrfFieldControlTypeChoices.DATE: "subject/components/controls/_date_picker_control.html",
    CrfFieldControlTypeChoices.DATE_TEXT: "subject/components/controls/_date_text_control.html",
    CrfFieldControlTypeChoices.DATETIME: "subject/components/controls/_datetime_control.html",
    CrfFieldControlTypeChoices.DATETIME_TEXT: "subject/components/controls/_datetime_text_control.html",
    "TIME": "subject/components/controls/_time_control.html",
    CrfFieldControlTypeChoices.LABEL_ONLY: "subject/components/controls/_label_only_control.html",
}


_CONTROL_I18N_MAP = {
    CrfFieldControlTypeChoices.TEXT: {
        "placeholder": _("Enter text"),
    },
    CrfFieldControlTypeChoices.TEXTAREA: {
        "placeholder": _("Enter text"),
    },
    CrfFieldControlTypeChoices.NUMBER: {
        "placeholder": _("Enter number"),
    },
    CrfFieldControlTypeChoices.SELECT: {
        "empty_option": _("-- Select --"),
    },
    CrfFieldControlTypeChoices.SELECT2: {
        "placeholder": _("Search or enter value"),
    },
    CrfFieldControlTypeChoices.RADIO: {
        "empty_option": _("No options"),
        "clear_option": _("Clear"),
    },
    CrfFieldControlTypeChoices.CHECKBOX: {
        "default_label": _("Checked"),
    },
    CrfFieldControlTypeChoices.MULTI_SELECT: {
        "empty_option": _("No options"),
    },
    CrfFieldControlTypeChoices.DATE: {
        "day_label": _("Day"),
        "month_label": _("Month"),
        "year_label": _("Year"),
        "day_placeholder": _("DD"),
        "month_empty_option": _("--"),
        "year_placeholder": _("YYYY"),
        "months": (
            {"value": "1", "label": _("January")},
            {"value": "2", "label": _("February")},
            {"value": "3", "label": _("March")},
            {"value": "4", "label": _("April")},
            {"value": "5", "label": _("May")},
            {"value": "6", "label": _("June")},
            {"value": "7", "label": _("July")},
            {"value": "8", "label": _("August")},
            {"value": "9", "label": _("September")},
            {"value": "10", "label": _("October")},
            {"value": "11", "label": _("November")},
            {"value": "12", "label": _("December")},
        ),
    },
    CrfFieldControlTypeChoices.DATE_TEXT: {
        "label": _("Date"),
    },
    CrfFieldControlTypeChoices.DATETIME: {
        "time_label": _("Time"),
        "time_placeholder": _("HH:MM"),
    },
    CrfFieldControlTypeChoices.DATETIME_TEXT: {
        "label": _("DateTime"),
    },
    "TIME": {
        "time_label": _("Time"),
        "time_placeholder": _("HH:MM"),
        "placeholder": _("HH:MM"),
    },
    CrfFieldControlTypeChoices.LABEL_ONLY: {
        "placeholder": _("Display value"),
    },
}


_CONTROL_TYPE_ALIAS_MAP = {
    "ENTRY_BOX": CrfFieldControlTypeChoices.TEXT,
    "TEXTBOX": CrfFieldControlTypeChoices.TEXT,
    "TEXT_BOX": CrfFieldControlTypeChoices.TEXT,
    "TEXT_AREA": CrfFieldControlTypeChoices.TEXTAREA,
    "DROPDOWN": CrfFieldControlTypeChoices.SELECT,
    "DROPDOWN_LIST": CrfFieldControlTypeChoices.SELECT,
    "SELECT2": CrfFieldControlTypeChoices.SELECT2,
    "SELECT_2": CrfFieldControlTypeChoices.SELECT2,
    "RADIO_BUTTON_LIST": CrfFieldControlTypeChoices.RADIO,
    "CHECKBOX_LIST": CrfFieldControlTypeChoices.MULTI_SELECT,
    "DATE_PICKER": CrfFieldControlTypeChoices.DATE,
    "DATE_TEXT": CrfFieldControlTypeChoices.DATE_TEXT,
    "TIME": "TIME",
    "TIME_PICKER": "TIME",
    "DATETIME_TEXT": CrfFieldControlTypeChoices.DATETIME_TEXT,
    "LABEL_ONLY": CrfFieldControlTypeChoices.LABEL_ONLY,
    "LABEL_ONLY_FIELD": CrfFieldControlTypeChoices.LABEL_ONLY,
}


def _normalize_control_type(raw_control_type):
    if not raw_control_type:
        return CrfFieldControlTypeChoices.TEXT
    normalized_value = re.sub(r"\s+", "_", str(raw_control_type).strip().upper())
    normalized_value = normalized_value.replace("-", "_")
    if normalized_value in CrfFieldControlTypeChoices.values:
        return normalized_value
    return _CONTROL_TYPE_ALIAS_MAP.get(normalized_value)


@register.simple_tag
def subject_control_template(control_type):
    normalized_control_type = _normalize_control_type(control_type)
    if not normalized_control_type:
        return ""
    return _CONTROL_TEMPLATE_MAP.get(normalized_control_type, "")


@register.simple_tag
def subject_control_i18n(control_type):
    normalized_control_type = _normalize_control_type(control_type)
    if not normalized_control_type:
        return {}
    return _CONTROL_I18N_MAP.get(normalized_control_type, {})


@register.simple_tag
def subject_control_tabindex(field, offset=0):
    if not isinstance(field, dict):
        return 0
    try:
        display_order = int(field.get("display_order") or 0)
        offset_value = int(offset or 0)
    except (TypeError, ValueError):
        return 0
    return (display_order * 20) + offset_value


@register.filter
def sort_fields_by_display_order(fields):
    def sort_key(field):
        if not isinstance(field, dict):
            return 999999, ""
        try:
            display_order = int(field.get("display_order") or 999999)
        except (TypeError, ValueError):
            display_order = 999999
        return display_order, str(field.get("label") or field.get("field_key") or "").lower()

    return sorted(fields or (), key=sort_key)


@register.simple_tag
def subject_text_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.TEXT)


@register.simple_tag
def subject_textarea_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.TEXTAREA)


@register.simple_tag
def subject_number_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.NUMBER)


@register.simple_tag
def subject_select_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.SELECT)


@register.simple_tag
def subject_select2_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.SELECT2)


@register.simple_tag
def subject_radio_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.RADIO)


@register.simple_tag
def subject_checkbox_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.CHECKBOX)


@register.simple_tag
def subject_multi_select_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.MULTI_SELECT)


@register.simple_tag
def subject_date_picker_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.DATE)


def _language_code_from_context(context):
    language_code = str(context.get("LANGUAGE_CODE") or get_language() or "").strip().lower()
    return "vi" if language_code.startswith("vi") else "en"


@register.simple_tag(takes_context=True)
def subject_date_text_control_i18n(context):
    locale = _language_code_from_context(context)
    return {
        **subject_control_i18n(CrfFieldControlTypeChoices.DATE_TEXT),
        "locale": locale,
        "placeholder": "dd/MM/yyyy" if locale == "vi" else "MM/dd/yyyy",
        "pattern": (
            r"^(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4}$"
            if locale == "vi"
            else r"^(?:0[1-9]|1[0-2])/(?:0[1-9]|[12][0-9]|3[01])/\d{4}$"
        ),
    }


@register.simple_tag
def subject_datetime_control_i18n():
    date_i18n = subject_control_i18n(CrfFieldControlTypeChoices.DATE)
    datetime_i18n = subject_control_i18n(CrfFieldControlTypeChoices.DATETIME)
    return {
        **date_i18n,
        **datetime_i18n,
    }


@register.simple_tag(takes_context=True)
def subject_datetime_text_control_i18n(context):
    locale = _language_code_from_context(context)
    return {
        **subject_control_i18n(CrfFieldControlTypeChoices.DATETIME_TEXT),
        "locale": locale,
        "placeholder": "dd/MM/yyyy HH:mm" if locale == "vi" else "MM/dd/yyyy HH:mm",
        "pattern": (
            r"^(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4} "
            r"(?:[01][0-9]|2[0-3]):[0-5][0-9]$"
            if locale == "vi"
            else r"^(?:0[1-9]|1[0-2])/(?:0[1-9]|[12][0-9]|3[01])/\d{4} "
            r"(?:[01][0-9]|2[0-3]):[0-5][0-9]$"
        ),
    }


@register.simple_tag
def subject_time_control_i18n():
    return subject_control_i18n("TIME")


def _normalize_date_input_value(raw_value):
    if isinstance(raw_value, dict):
        raw_value = raw_value.get("__date") or raw_value.get("date") or raw_value.get("value") or ""
    text = str(raw_value or "").strip()
    if not text:
        return ""

    match = re.search(r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})", text)
    if not match:
        return ""
    try:
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))
    except (TypeError, ValueError):
        return ""
    if year < 1 or month < 1 or month > 12 or day < 1 or day > 31:
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


@register.simple_tag
def subject_date_input_value(field):
    if not isinstance(field, dict):
        return ""
    normalized_value = _normalize_date_input_value(field.get("value"))
    if normalized_value:
        return normalized_value
    return _normalize_date_input_value(
        f"{field.get('date_year') or ''}-{field.get('date_month') or ''}-{field.get('date_day') or ''}"
    )


def _normalize_time_input_value(raw_value):
    if isinstance(raw_value, dict):
        raw_value = raw_value.get("__time") or raw_value.get("time") or ""
    text = str(raw_value or "").strip()
    if not text:
        return ""

    match = re.search(
        r"(?:^|[T\s])(?P<hour>\d{1,2}):(?P<minute>\d{1,2})"
        r"(?::(?P<second>\d{1,2})(?:\.\d{1,3})?)?(?:$|[+\-Z\s])",
        text,
    )
    if not match:
        return ""
    try:
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        second_text = match.group("second")
        second = int(second_text) if second_text is not None else 0
    except (TypeError, ValueError):
        return ""
    if hour < 0 or hour > 23 or minute < 0 or minute > 59 or second < 0 or second > 59:
        return ""
    return f"{hour:02d}:{minute:02d}"


@register.simple_tag
def subject_time_input_value(field):
    if not isinstance(field, dict):
        return ""
    normalized_value = _normalize_time_input_value(field.get("value"))
    if normalized_value:
        return normalized_value
    return _normalize_time_input_value(field.get("date_time"))


@register.simple_tag
def subject_label_only_control_i18n():
    return subject_control_i18n(CrfFieldControlTypeChoices.LABEL_ONLY)


@register.filter
def subject_form_status_label(raw_status):
    normalized_status = (str(raw_status).strip().lower() if raw_status is not None else "")
    if normalized_status in {"", "none", "null", "not_started", "not_start"}:
        return _("Not Start")
    if normalized_status == "in_progress":
        return _("In Process")
    if normalized_status == "under_review":
        return _("Under Review")
    if normalized_status == "correction_required":
        return _("Correction Required")
    if normalized_status == "submitted":
        return _("Submitted")
    if normalized_status == "verified":
        return _("Verified")
    if normalized_status == "locked":
        return _("Locked")
    if normalized_status == "finalized":
        return _("Finalized")
    return str(raw_status or "")

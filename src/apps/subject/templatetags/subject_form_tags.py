import re

from django import template
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
    CrfFieldControlTypeChoices.DATETIME: "subject/components/controls/_datetime_control.html",
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
    CrfFieldControlTypeChoices.DATETIME: {
        "time_label": _("Time"),
        "time_placeholder": _("HH:MM"),
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
    "TIME_PICKER": CrfFieldControlTypeChoices.DATETIME,
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


@register.simple_tag
def subject_datetime_control_i18n():
    date_i18n = subject_control_i18n(CrfFieldControlTypeChoices.DATE)
    datetime_i18n = subject_control_i18n(CrfFieldControlTypeChoices.DATETIME)
    return {
        **date_i18n,
        **datetime_i18n,
    }


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

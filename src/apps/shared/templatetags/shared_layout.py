import datetime

from django import template
from django.core.exceptions import ImproperlyConfigured
from django.utils.formats import get_format
from django.utils.translation import gettext_lazy as _

from apps.shared.datetime_formatting import date_format

register = template.Library()


@register.simple_tag(takes_context=True)
def require_authenticate_template_view(context):
    auth_user = context.get("auth_user")
    if auth_user is None:
        raise ImproperlyConfigured(
            "shared/_layout.html requires `auth_user` in the template context. "
            "Use `AuthenticateTemplateView` or `AuthenticateTemplateContextMixin` "
            "for any view that extends this layout."
        )

    return ""


@register.inclusion_tag("shared/components/_layout_detail_meta.html", takes_context=True)
def render_layout_detail_meta(context):
    return {
        "layout_detail_meta_items": context.get("layout_detail_meta_items") or (),
    }


@register.inclusion_tag("study/components/_event_definitions_diagram_panel.html", takes_context=True)
def render_event_definitions_diagram_panel(context):
    return {
        "event_definitions_diagram_title": _("Event Flow"),
        "event_definitions_diagram_note": _("Visualized from event definitions and transition rules."),
        "event_definitions_diagram_aria_label": _("Event definitions flow diagram"),
        "event_definitions_diagram_has_nodes": bool(context.get("event_definitions_diagram_has_nodes")),
        "event_definitions_diagram_mermaid": context.get("event_definitions_diagram_mermaid") or "",
    }


@register.simple_tag
def shared_locale_format(format_name):
    resolved_format = get_format(format_name)
    if isinstance(resolved_format, (list, tuple)):
        return resolved_format[0] if resolved_format else ""
    return resolved_format or ""


@register.filter
def shared_picker_value(value, format_name):
    if value in (None, ""):
        return ""
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return date_format(value, format_name)
    return str(value)


@register.simple_tag
def subject_date_picker_i18n():
    return {
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
    }

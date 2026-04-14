from django import template
from django.core.exceptions import ImproperlyConfigured
from django.utils.formats import date_format, get_format
from django.utils.translation import gettext_lazy as _
import datetime

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

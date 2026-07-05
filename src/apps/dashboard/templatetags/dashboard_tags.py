from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.simple_tag
def dashboard_i18n_labels():
    return {
        "site_filter_placeholder": _("All Sites"),
        "site_filter_aria_label": _("Filter dashboard by site"),
    }


@register.inclusion_tag("dashboard/blocks/_hero.html", takes_context=True)
def render_dashboard_hero(context):
    return {
        "dashboard_selected_study_label": context.get("dashboard_selected_study_label", ""),
        "dashboard_scope_summary": context.get("dashboard_scope_summary", {}),
    }


@register.inclusion_tag("dashboard/blocks/_filter_bar.html", takes_context=True)
def render_dashboard_filter_bar(context):
    return {
        "dashboard_site_filter_options": context.get("dashboard_site_filter_options", ()),
    }


@register.inclusion_tag("dashboard/blocks/_overview_cards.html", takes_context=True)
def render_dashboard_overview_cards(context):
    return {
        "dashboard_overview_cards": context.get("dashboard_overview_cards", ()),
    }


@register.inclusion_tag("dashboard/blocks/_query_panel.html", takes_context=True)
def render_dashboard_query_panel(context):
    return {
        "dashboard_query_rows": context.get("dashboard_query_rows", ()),
        "dashboard_query_total": context.get("dashboard_query_total", 0),
    }


@register.inclusion_tag("dashboard/blocks/_enrollment_panel.html", takes_context=True)
def render_dashboard_enrollment_panel(context):
    return {
        "dashboard_enrollment_rows": context.get("dashboard_enrollment_rows", ()),
    }


@register.inclusion_tag("dashboard/blocks/_execution_panel.html", takes_context=True)
def render_dashboard_execution_panel(context):
    return {
        "dashboard_execution_rows": context.get("dashboard_execution_rows", ()),
    }


@register.inclusion_tag("dashboard/blocks/_priority_panel.html", takes_context=True)
def render_dashboard_priority_panel(context):
    return {
        "dashboard_priority_rows": context.get("dashboard_priority_rows", ()),
    }


@register.inclusion_tag("dashboard/blocks/_randomization_panel.html", takes_context=True)
def render_dashboard_randomization_panel(context):
    return {
        "dashboard_randomization_rows": context.get("dashboard_randomization_rows", ()),
    }

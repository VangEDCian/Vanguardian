from django import template
from django.core.exceptions import ImproperlyConfigured

register = template.Library()


@register.simple_tag(takes_context=True)
def require_authenticate_template_view(context):
    auth_user = context.get("auth_user")
    if auth_user is None:
        raise ImproperlyConfigured(
            "shared/_layout.html requires `auth_user` in the template context. "
            "Use `AuthenticateTemplateView` for any template view that extends this layout."
        )

    return ""


@register.inclusion_tag("shared/components/_layout_detail_meta.html", takes_context=True)
def render_layout_detail_meta(context):
    return {
        "layout_detail_meta_items": context.get("layout_detail_meta_items") or (),
    }

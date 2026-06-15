import re

from django import template

from apps.identity.application.permissions import ALL_PERMISSION_DEFINITIONS
from apps.identity.public import ContextualAuthorizationService, user_bypasses_context_permission

register = template.Library()

APP_PERMISSION_KEY_PREFIXES = {
    "dashboard": "DASHBOARD",
    "identity": "USERS",
    "reconcile": "QUERIES",
    "site": "SITES",
    "study": "STUDIES",
    "subject": "SUBJECTS",
}

APP_PERMISSION_CONTEXT_TOKENS = {
    "dashboard": {"dashboard"},
    "identity": {"identity", "user", "users"},
    "reconcile": {"dataquery", "dataqueries", "query", "queries"},
    "site": {"site", "sites"},
    "study": {"study", "studies"},
    "subject": {"subject", "subjects"},
}


@register.simple_tag(takes_context=True)
def get_user_permission_flags(context, user=None, study_id=None, site_id=None):
    request = context.get("request")
    if user is None:
        user = getattr(request, "user", None)
    if study_id is None:
        study_id = context.get("shared_study_selected_id")
    if site_id is None:
        site_id = context.get("shared_site_selected_id")

    return build_user_permission_flags(
        user,
        study_id=_optional_int(study_id),
        site_id=_optional_int(site_id),
        request=request,
    )


def build_user_permission_flags(user, *, study_id=None, site_id=None, request=None):
    permission_codes = [definition.permission_code for definition in ALL_PERMISSION_DEFINITIONS]
    if user_bypasses_context_permission(user):
        return {
            permission_template_key(permission_code): True
            for permission_code in permission_codes
        }
    if not getattr(user, "is_authenticated", False):
        return {
            permission_template_key(permission_code): False
            for permission_code in permission_codes
        }

    authorization = ContextualAuthorizationService(request=request)
    return {
        permission_template_key(permission_code): authorization.can(
            user,
            permission_code,
            study_id=study_id,
            study_site_id=site_id,
        ).allowed
        for permission_code in permission_codes
    }


def permission_template_key(permission_code):
    permission_code = str(permission_code or "").strip()
    if "." in permission_code and permission_code == permission_code.upper():
        return _normalize_key(permission_code)
    if "." not in permission_code:
        return _normalize_key(permission_code)

    app_label, codename = permission_code.split(".", 1)
    prefix = APP_PERMISSION_KEY_PREFIXES.get(app_label, app_label.upper())
    context_tokens = APP_PERMISSION_CONTEXT_TOKENS.get(app_label, {app_label})
    codename_parts = [
        part
        for part in codename.split("_")
        if part and part.lower() not in context_tokens
    ]
    suffix = "_".join(codename_parts) or codename
    return _normalize_key(f"{prefix}_{suffix}")


def _normalize_key(value):
    return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")


def _optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

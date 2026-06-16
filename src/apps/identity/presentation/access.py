from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest

from apps.identity.application.authorization import (
    AuthorizationContext,
    ContextualAuthorizationService,
    user_bypasses_context_permission,
)

SCOPE_ANY = "ANY"
SCOPE_STUDY = "STUDY"
SCOPE_STUDY_SITE = "STUDY_SITE"


def authorization_scope_flags(scope: str) -> tuple[bool, bool]:
    normalized_scope = str(scope or SCOPE_ANY).upper()
    if normalized_scope == SCOPE_STUDY:
        return True, False
    if normalized_scope == SCOPE_STUDY_SITE:
        return False, True
    return True, True


def ensure_authenticated(request):
    if getattr(request.user, "is_authenticated", False):
        return None
    return redirect_to_login(request.get_full_path())


def get_authorization_context(request) -> AuthorizationContext:
    return getattr(
        request,
        "authorization_context",
        AuthorizationContext(study_id=None, study_site_id=None, source="none", raw={}),
    )


def validate_required_context(
    context: AuthorizationContext,
    *,
    require_study: bool,
    require_site: bool,
) -> HttpResponseBadRequest | None:
    if not context.is_valid:
        return HttpResponseBadRequest(context.error or "Malformed authorization context.")
    if require_study and context.study_id is None:
        return HttpResponseBadRequest("Missing study authorization context.")
    if require_site and context.study_site_id is None:
        return HttpResponseBadRequest("Missing study-site authorization context.")
    return None


def enforce_context_permission(
    request,
    *,
    permission: str,
    scope: str,
    require_study: bool,
    require_site: bool,
):
    unauthenticated_response = ensure_authenticated(request)
    if unauthenticated_response is not None:
        return unauthenticated_response

    context = get_authorization_context(request)
    if user_bypasses_context_permission(request.user):
        return validate_required_context(context, require_study=False, require_site=False)

    bad_context_response = validate_required_context(
        context,
        require_study=require_study,
        require_site=require_site,
    )
    if bad_context_response is not None:
        return bad_context_response

    allow_study_scope, allow_site_scope = authorization_scope_flags(scope)
    decision = ContextualAuthorizationService(request=request).can(
        user=request.user,
        permission=permission,
        study_id=context.study_id,
        study_site_id=context.study_site_id,
        allow_study_scope=allow_study_scope,
        allow_site_scope=allow_site_scope,
    )
    if not decision.allowed:
        raise PermissionDenied(decision.reason)
    return None

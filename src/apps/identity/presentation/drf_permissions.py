from rest_framework.exceptions import ParseError
from rest_framework.permissions import BasePermission

from apps.identity.application.authorization import ContextualAuthorizationService
from apps.identity.presentation.access import (
    authorization_scope_flags,
    get_authorization_context,
    user_bypasses_context_permission,
)


class ContextPermission(BasePermission):
    def has_permission(self, request, view):
        permission = getattr(view, "context_permission_required", None) or getattr(view, "permission_required", "")
        if isinstance(permission, (list, tuple)):
            permission = permission[0] if permission else ""
        if not permission:
            return True

        context = get_authorization_context(request)
        if not context.is_valid:
            raise ParseError(context.error or "Malformed authorization context.")
        if user_bypasses_context_permission(request.user):
            return True
        if getattr(view, "require_study_context", True) and context.study_id is None:
            raise ParseError("Missing study authorization context.")
        if getattr(view, "require_site_context", False) and context.study_site_id is None:
            raise ParseError("Missing study-site authorization context.")

        allow_study_scope, allow_site_scope = authorization_scope_flags(
            getattr(view, "authorization_scope", "ANY"),
        )
        decision = ContextualAuthorizationService(request=request).can(
            user=request.user,
            permission=permission,
            study_id=context.study_id,
            study_site_id=context.study_site_id,
            allow_study_scope=allow_study_scope,
            allow_site_scope=allow_site_scope,
        )
        return decision.allowed

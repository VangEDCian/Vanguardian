import logging
from dataclasses import dataclass, field

from django.conf import settings
from django.core.exceptions import PermissionDenied

from apps.identity.infrastructure.auth.contextual_authorization import ContextualAuthorizationRepository

logger = logging.getLogger(__name__)

AuthorizationScope = str


@dataclass(frozen=True)
class AuthorizationContext:
    study_id: int | None
    study_site_id: int | None
    source: str
    raw: dict = field(default_factory=dict)
    is_valid: bool = True
    error: str = ""


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    matched_scope: AuthorizationScope | None
    matched_role_id: int | None
    permission: str


def user_bypasses_context_permission(user) -> bool:
    return (
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", True)
        and getattr(user, "is_superuser", False)
    )


class ContextualAuthorizationService:
    """
    Permission grants action. Membership grants scope. Active role assignment
    connects permission to scope.
    """

    def __init__(self, *, repository=None, request=None):
        self.repository = repository or ContextualAuthorizationRepository()
        self.request = request

    def can(
        self,
        user,
        permission: str,
        *,
        study_id: int | None = None,
        study_site_id: int | None = None,
        allow_study_scope: bool = True,
        allow_site_scope: bool = True,
    ) -> AuthorizationDecision:
        cache_key = (
            getattr(user, "id", None),
            permission,
            study_id,
            study_site_id,
            allow_study_scope,
            allow_site_scope,
        )
        cached_decision = self._get_cached_decision(cache_key)
        if cached_decision is not None:
            return cached_decision

        decision = self._can_uncached(
            user,
            permission,
            study_id=study_id,
            study_site_id=study_site_id,
            allow_study_scope=allow_study_scope,
            allow_site_scope=allow_site_scope,
        )
        self._set_cached_decision(cache_key, decision)
        if not decision.allowed:
            self._log_denial(decision=decision, study_id=study_id, study_site_id=study_site_id)
        return decision

    def require(self, user, permission: str, **kwargs) -> AuthorizationDecision:
        decision = self.can(user, permission, **kwargs)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)
        return decision

    def _can_uncached(
        self,
        user,
        permission: str,
        *,
        study_id: int | None,
        study_site_id: int | None,
        allow_study_scope: bool,
        allow_site_scope: bool,
    ) -> AuthorizationDecision:
        if not getattr(user, "is_authenticated", False):
            return self._deny(str(permission or ""), "USER_UNAUTHENTICATED")
        if not getattr(user, "is_active", False):
            return self._deny(str(permission or ""), "USER_INACTIVE")
        if user_bypasses_context_permission(user):
            return self._allow(str(permission or ""), "GLOBAL", None)

        permission_lookup = self.repository.resolve_permission(permission)
        normalized_permission = permission_lookup.code if permission_lookup is not None else str(permission or "")

        if permission_lookup is None:
            return self._deny(normalized_permission, "PERMISSION_NOT_FOUND")

        if study_id is None:
            if getattr(settings, "AUTHZ_ALLOW_GLOBAL_ROLE_FOR_STUDY_CONTEXT", False):
                global_match = self.repository.find_global_role_match(user_id=user.pk, permission_id=permission_lookup.id)
                if global_match is not None:
                    return self._allow(normalized_permission, global_match.scope, global_match.role_id)
            return self._deny(normalized_permission, "STUDY_CONTEXT_REQUIRED")

        if study_site_id is not None and not self.repository.study_site_belongs_to_study(
            study_id=study_id,
            study_site_id=study_site_id,
        ):
            return self._deny(normalized_permission, "INVALID_STUDY_SITE_CONTEXT")

        if allow_site_scope and study_site_id is not None:
            site_match = self.repository.find_study_site_role_match(
                user_id=user.pk,
                study_id=study_id,
                study_site_id=study_site_id,
                permission_id=permission_lookup.id,
            )
            if site_match is not None:
                return self._allow(normalized_permission, site_match.scope, site_match.role_id)

        if allow_study_scope:
            study_match = self.repository.find_study_role_match(
                user_id=user.pk,
                study_id=study_id,
                permission_id=permission_lookup.id,
            )
            if study_match is not None:
                return self._allow(normalized_permission, study_match.scope, study_match.role_id)

        return self._deny(normalized_permission, self._deny_reason(user, study_id, study_site_id, allow_site_scope))

    def _deny_reason(self, user, study_id: int, study_site_id: int | None, allow_site_scope: bool) -> str:
        if not self.repository.has_active_study_membership(user_id=user.pk, study_id=study_id):
            return "NO_ACTIVE_STUDY_MEMBERSHIP"
        if study_site_id is not None and allow_site_scope:
            if not self.repository.has_active_study_site_membership(
                user_id=user.pk,
                study_id=study_id,
                study_site_id=study_site_id,
            ):
                return "NO_ACTIVE_STUDY_SITE_MEMBERSHIP"
            if not self.repository.has_active_study_site_role_assignment(
                user_id=user.pk,
                study_id=study_id,
                study_site_id=study_site_id,
            ) and not self.repository.has_active_study_role_assignment(user_id=user.pk, study_id=study_id):
                return "ROLE_NOT_ASSIGNED"
        elif not self.repository.has_active_study_role_assignment(user_id=user.pk, study_id=study_id):
            return "ROLE_NOT_ASSIGNED"
        return "PERMISSION_NOT_GRANTED"

    def _get_cached_decision(self, cache_key):
        if self.request is None:
            return None
        cache = getattr(self.request, "_contextual_authorization_cache", None)
        if cache is None:
            cache = {}
            setattr(self.request, "_contextual_authorization_cache", cache)
        return cache.get(cache_key)

    def _set_cached_decision(self, cache_key, decision: AuthorizationDecision) -> None:
        if self.request is None:
            return
        cache = getattr(self.request, "_contextual_authorization_cache", None)
        if cache is None:
            cache = {}
            setattr(self.request, "_contextual_authorization_cache", cache)
        cache[cache_key] = decision

    def _log_denial(self, *, decision: AuthorizationDecision, study_id: int | None, study_site_id: int | None) -> None:
        request = self.request
        if request is None:
            return
        logger.info(
            "contextual_authorization_denied",
            extra={
                "user_id": getattr(getattr(request, "user", None), "id", None),
                "permission": decision.permission,
                "study_id": study_id,
                "study_site_id": study_site_id,
                "reason": decision.reason,
                "path": getattr(request, "path", ""),
                "method": getattr(request, "method", ""),
                "request_id": self._request_id(request),
            },
        )

    @staticmethod
    def _request_id(request):
        return (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or getattr(request, "request_id", None)
        )

    @staticmethod
    def _allow(permission: str, matched_scope: AuthorizationScope, matched_role_id: int | None) -> AuthorizationDecision:
        return AuthorizationDecision(
            allowed=True,
            reason="ALLOWED",
            matched_scope=matched_scope,
            matched_role_id=matched_role_id,
            permission=permission,
        )

    @staticmethod
    def _deny(permission: str, reason: str) -> AuthorizationDecision:
        return AuthorizationDecision(
            allowed=False,
            reason=reason,
            matched_scope=None,
            matched_role_id=None,
            permission=permission,
        )

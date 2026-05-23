from django.contrib.auth import logout
from django.db import DatabaseError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from apps.identity.infrastructure.auth.constants import PASSWORD_RESET_BYPASS_SESSION_KEY
from apps.identity.infrastructure.auth.session_state import is_single_active_session_valid
from apps.identity.infrastructure.persistence.models import (
    StudyMembership,
    StudySiteMembership,
)
from apps.shared.application.services.cookies import CookiesService


class SingleActiveSessionMiddleware:
    EXCLUDED_PATH_PREFIXES = (
        reverse("identity:login"),
        reverse("identity:logout"),
        reverse("set_language"),
        "/i18n/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_skip(request) or is_single_active_session_valid(request):
            return self.get_response(request)

        logout(request)
        if self._expects_json(request):
            response = JsonResponse(
                {
                    "authenticated": False,
                    "session_valid": False,
                    "reason": "signed_in_elsewhere",
                    "login_url": reverse("identity:login"),
                },
                status=409,
            )
        else:
            response = render(
                request,
                "identity/session_invalidated.html",
                {
                    "login_url": reverse("identity:login"),
                },
                status=401,
            )
        CookiesService.reset_cookies(response=response)
        return response

    def _should_skip(self, request):
        if not getattr(request.user, "is_authenticated", False):
            return True
        return request.path_info.startswith(self.EXCLUDED_PATH_PREFIXES)

    def _expects_json(self, request):
        return (
            request.path_info.startswith("/api/")
            or request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )


class MembershipAccessMiddleware:
    EXEMPT_PATH_PREFIXES = (
        "/login/",
        "/logout/",
        "/forgot-password/",
        "/reset-password/",
        "/i18n/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_skip(request):
            return self.get_response(request)

        if self._has_membership(request.user.id):
            return self.get_response(request)

        return render(
            request,
            "identity/access_denied.html",
            status=403,
        )

    def _should_skip(self, request):
        if request.path_info.startswith(self.EXEMPT_PATH_PREFIXES):
            return True

        if not request.user.is_authenticated:
            return True

        return request.user.is_superuser

    def _has_membership(self, user_id):
        try:
            if StudyMembership.objects.filter(user_id=user_id, deleted=False).exists():
                return True

            return StudySiteMembership.objects.filter(user_id=user_id, deleted=False).exists()
        except DatabaseError:
            return False


class CheckFirstLoginMiddleware:
    EXCLUDED_PATH_PREFIXES = (
        reverse("identity:login"),
        reverse("identity:first_login"),
        reverse("identity:logout"),
        reverse("set_language"),
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_excluded_path = request.path_info.startswith(self.EXCLUDED_PATH_PREFIXES)

        if (
                request.user.is_authenticated
                and hasattr(request.user, "attempt_login")
                and request.user.attempt_login <= 0
                and not self._has_password_reset_bypass(request)
                and not is_excluded_path
        ):
            return HttpResponseRedirect(reverse('identity:first_login'))
        response = self.get_response(request)
        return response

    def _has_password_reset_bypass(self, request):
        if not getattr(request.user, "pk", None):
            return False
        session = getattr(request, "session", {})
        bypass_user_ids = set(session.get(PASSWORD_RESET_BYPASS_SESSION_KEY, []))
        return str(request.user.pk) in bypass_user_ids

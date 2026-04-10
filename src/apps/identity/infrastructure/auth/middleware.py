from django.db import DatabaseError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from apps.identity.infrastructure.persistence.models import (
    StudyMembership,
    StudySiteMembership,
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
    EXCLUDES_PATH = [
        reverse("identity:login"),
        reverse("identity:first_login"),
        reverse("identity:logout"),
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
                request.user.is_authenticated
                and hasattr(request.user, "attempt_login")
                and request.user.attempt_login <= 0
                and request.path not in self.EXCLUDES_PATH
        ):
            return HttpResponseRedirect(reverse('identity:first_login'))
        response = self.get_response(request)
        return response

import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from apps.identity.infrastructure.auth.constants import PASSWORD_RESET_BYPASS_SESSION_KEY
from apps.identity.infrastructure.auth.middleware import CheckFirstLoginMiddleware, SingleActiveSessionMiddleware


class CheckFirstLoginMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _build_middleware(self):
        return CheckFirstLoginMiddleware(lambda request: self._ok_response())

    @staticmethod
    def _ok_response():
        from django.http import HttpResponse

        return HttpResponse(status=200)

    @staticmethod
    def _first_login_user(attempt_login=0):
        return SimpleNamespace(
            is_authenticated=True,
            attempt_login=attempt_login,
        )

    def test_allows_i18n_path_for_first_login_user(self):
        middleware = self._build_middleware()
        request = self.factory.post("/i18n/setlang/")
        request.user = cast(Any, self._first_login_user(attempt_login=0))

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_redirects_protected_path_for_first_login_user(self):
        middleware = self._build_middleware()
        request = self.factory.get("/dashboard/")
        request.user = cast(Any, self._first_login_user(attempt_login=0))

        response = middleware(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("identity:first_login"))

    def test_allows_first_login_path(self):
        middleware = self._build_middleware()
        request = self.factory.get(reverse("identity:first_login"))
        request.user = cast(Any, self._first_login_user(attempt_login=0))

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_allows_login_path(self):
        middleware = self._build_middleware()
        request = self.factory.get(reverse("identity:login"))
        request.user = cast(Any, self._first_login_user(attempt_login=0))

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_allows_logout_path(self):
        middleware = self._build_middleware()
        request = self.factory.get(reverse("identity:logout"))
        request.user = cast(Any, self._first_login_user(attempt_login=0))
        request.session = {}

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_allows_protected_path_when_password_reset_bypass_exists(self):
        middleware = self._build_middleware()
        request = self.factory.get("/dashboard/")
        request.user = cast(Any, SimpleNamespace(is_authenticated=True, attempt_login=0, pk=7))
        request.session = {
            PASSWORD_RESET_BYPASS_SESSION_KEY: ["7"],
        }

        response = middleware(request)

        self.assertEqual(response.status_code, 200)


class SingleActiveSessionMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _build_middleware(self):
        return SingleActiveSessionMiddleware(lambda request: self._ok_response())

    @staticmethod
    def _ok_response():
        from django.http import HttpResponse

        return HttpResponse(status=200)

    @staticmethod
    def _user(active_session_key):
        return SimpleNamespace(
            is_authenticated=True,
            pk=7,
            active_session_key=active_session_key,
        )

    def test_allows_current_active_session(self):
        middleware = self._build_middleware()
        request = self.factory.get("/dashboard/")
        request.user = cast(Any, self._user(active_session_key="current-session"))
        request.session = SimpleNamespace(session_key="current-session")

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_logs_out_stale_json_request(self):
        middleware = self._build_middleware()
        request = self.factory.get("/api/session/status", HTTP_ACCEPT="application/json")
        request.user = cast(Any, self._user(active_session_key="new-session"))
        request.session = SimpleNamespace(session_key="old-session")

        with patch("apps.identity.infrastructure.auth.middleware.logout") as logout_user:
            response = middleware(request)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.content)["reason"], "signed_in_elsewhere")
        logout_user.assert_called_once_with(request)

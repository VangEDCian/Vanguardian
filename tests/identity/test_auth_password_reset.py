from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase

from apps.identity.infrastructure.auth.constants import PASSWORD_RESET_BYPASS_SESSION_KEY
from apps.identity.presentation.web.views.auth import (
    IdentityLoginView,
    IdentityResetPasswordConfirmView,
)


class _Session(dict):
    modified = False


class IdentityResetPasswordConfirmViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_marks_session_to_bypass_first_login_after_reset(self):
        view = IdentityResetPasswordConfirmView()
        request = self.factory.post("/reset-password/mock/mock/")
        request.session = _Session()
        view.request = request
        audit_service = SimpleNamespace(record_user_reset_password=MagicMock())
        view.identity_user_audit_service_class = MagicMock(return_value=audit_service)
        form = SimpleNamespace(user=SimpleNamespace(pk=22))

        with patch(
            "django.contrib.auth.views.PasswordResetConfirmView.form_valid",
            return_value=HttpResponseRedirect("/login/"),
        ):
            response = view.form_valid(form)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/")
        self.assertEqual(request.session[PASSWORD_RESET_BYPASS_SESSION_KEY], ["22"])
        self.assertTrue(request.session.modified)
        audit_service.record_user_reset_password.assert_called_once()


class IdentityLoginViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_allows_login_without_first_login_when_bypass_marker_exists(self):
        request = self.factory.post("/login/", data={"username": "demo"})
        request.session = _Session({PASSWORD_RESET_BYPASS_SESSION_KEY: ["15"]})

        view = IdentityLoginView()
        view.request = request
        view.login_audit_service_class = MagicMock(
            return_value=SimpleNamespace(
                record_login_succeeded=MagicMock(),
                record_login_failed=MagicMock(),
            )
        )
        form = MagicMock()
        user = SimpleNamespace(
            pk=15,
            attempt_login=0,
            save=MagicMock(),
        )
        form.get_user.return_value = user

        with patch(
            "django.contrib.auth.views.LoginView.form_valid",
            return_value=HttpResponseRedirect("/dashboard/"),
        ):
            response = view.form_valid(form)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")
        user.save.assert_not_called()

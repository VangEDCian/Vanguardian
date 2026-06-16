from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.views import View

from apps.shared.views.generic.authenticate_template_view import AuthenticateTemplateContextMixin


class ProtectedView(AuthenticateTemplateContextMixin, View):
    permission_required = "subject.view_subject_detail"
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)


class GlobalProtectedView(AuthenticateTemplateContextMixin, View):
    permission_required = "dashboard.view_dashboard"
    require_study_context = False
    allow_global_permission_check = True
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)


class AuthenticateTemplateContextMixinTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(LOGIN_URL="/login/")
    def test_redirects_anonymous_user_before_permission_check(self):
        request = self.factory.get("/studies/1/subjects/2/?event=1&form=4")
        request.user = SimpleNamespace(is_authenticated=False)

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    def test_raises_permission_denied_after_authentication_without_context(self):
        request = self.factory.get("/studies/1/subjects/2/?event=1&form=4")
        request.user = SimpleNamespace(
            is_authenticated=True,
            has_perms=lambda permissions: False,
        )

        with self.assertRaises(PermissionDenied):
            ProtectedView.as_view()(request)

    def test_django_permission_does_not_bypass_missing_context(self):
        request = self.factory.get("/studies/1/subjects/2/?event=1&form=4")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            has_perms=lambda permissions: True,
        )

        with self.assertRaises(PermissionDenied):
            ProtectedView.as_view()(request)

    def test_superuser_bypasses_missing_context_and_permission_check(self):
        request = self.factory.get("/studies/1/subjects/2/?event=1&form=4")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_superuser=True,
            has_perms=lambda permissions: False,
        )

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    @patch("apps.shared.views.generic.authenticate_template_view.ContextualAuthorizationService")
    def test_allows_study_scoped_permission_from_authorization_service(self, authorization_service):
        authorization_service.return_value.can.return_value = SimpleNamespace(allowed=True)
        request = self.factory.get("/studies/1/subjects/2/?event=1&form=4")
        request.user = SimpleNamespace(
            is_authenticated=True,
            pk=99,
            has_perms=lambda permissions: False,
        )

        response = ProtectedView.as_view()(request, study_id=1)

        self.assertEqual(response.status_code, 200)
        authorization_service.return_value.can.assert_called_once()
        self.assertEqual(authorization_service.return_value.can.call_args.kwargs["user"], request.user)
        self.assertEqual(
            authorization_service.return_value.can.call_args.kwargs["permission"],
            "subject.view_subject_detail",
        )
        self.assertEqual(authorization_service.return_value.can.call_args.kwargs["study_id"], 1)

    def test_allows_explicit_global_permission_check_without_study_context(self):
        request = self.factory.get("/dashboard/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            has_perms=lambda permissions: True,
        )

        response = GlobalProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 200)

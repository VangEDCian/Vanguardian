from types import SimpleNamespace

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

    def test_raises_permission_denied_after_authentication(self):
        request = self.factory.get("/studies/1/subjects/2/?event=1&form=4")
        request.user = SimpleNamespace(
            is_authenticated=True,
            has_perms=lambda permissions: False,
        )

        with self.assertRaises(PermissionDenied):
            ProtectedView.as_view()(request)

    def test_allows_authenticated_user_with_required_permission(self):
        request = self.factory.get("/studies/1/subjects/2/?event=1&form=4")
        request.user = SimpleNamespace(
            is_authenticated=True,
            has_perms=lambda permissions: True,
        )

        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 200)

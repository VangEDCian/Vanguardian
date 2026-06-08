from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import path
from django.utils import timezone

from apps.identity.application.authorization import AuthorizationDecision
from apps.identity.presentation.decorators import require_context_permission
from apps.identity.presentation.middleware import AuthorizationContextMiddleware
from apps.study.models import Site, Study


@require_context_permission(
    "datacapture.change_pageentry",
    scope="ANY",
    require_study=True,
    require_site=True,
)
def decorated_context_view(request, study_id, site_id):
    return HttpResponse("ok")


urlpatterns = [
    path("decorated/<int:study_id>/<int:site_id>/", decorated_context_view),
]


class AuthorizationContextMiddlewareTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.factory = RequestFactory()
        self.study = Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code="STUDY-A",
            name="Study A",
            description="",
            is_active=True,
        )
        self.site = Site.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code="HCM01",
            name="Site HCM01",
            study=self.study,
            is_active=True,
        )
        self.other_study = Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code="STUDY-B",
            name="Study B",
            description="",
            is_active=True,
        )

    def test_middleware_resolves_context_from_route_kwargs(self):
        request = self.factory.get("/subjects/")
        request.user = SimpleNamespace(is_authenticated=True)
        middleware = AuthorizationContextMiddleware(lambda request: HttpResponse(status=200))

        middleware.process_view(request, lambda request: HttpResponse(), (), {"study_id": self.study.pk, "site_id": self.site.pk})

        self.assertEqual(request.authorization_context.source, "route")
        self.assertEqual(request.authorization_context.study_id, self.study.pk)
        self.assertEqual(request.authorization_context.study_site_id, self.site.pk)

    def test_query_and_header_context_cannot_override_route_kwargs(self):
        request = self.factory.get(
            f"/api/subjects/?study_id={self.other_study.pk}&study_site_id=999",
            HTTP_X_STUDY_ID=str(self.other_study.pk),
            HTTP_X_STUDY_SITE_ID="999",
            HTTP_ACCEPT="application/json",
        )
        request.user = SimpleNamespace(is_authenticated=True)
        middleware = AuthorizationContextMiddleware(lambda request: HttpResponse(status=200))

        middleware.process_view(request, lambda request: HttpResponse(), (), {"study_id": self.study.pk, "site_id": self.site.pk})

        self.assertEqual(request.authorization_context.source, "route")
        self.assertEqual(request.authorization_context.study_id, self.study.pk)
        self.assertEqual(request.authorization_context.study_site_id, self.site.pk)

    def test_middleware_marks_mismatched_study_site_context_invalid(self):
        request = self.factory.get("/subjects/")
        request.user = SimpleNamespace(is_authenticated=True)
        middleware = AuthorizationContextMiddleware(lambda request: HttpResponse(status=200))

        middleware.process_view(request, lambda request: HttpResponse(), (), {"study_id": self.other_study.pk, "site_id": self.site.pk})

        self.assertFalse(request.authorization_context.is_valid)
        self.assertEqual(request.authorization_context.error, "study_site_id does not belong to study_id.")

    def test_middleware_returns_400_for_malformed_protected_context(self):
        request = self.factory.get("/subjects/")
        request.user = SimpleNamespace(is_authenticated=True)
        middleware = AuthorizationContextMiddleware(lambda request: HttpResponse(status=200))

        response = middleware.process_view(request, decorated_context_view, (), {"study_id": "bad"})

        self.assertEqual(response.status_code, 400)

    def test_superuser_bypasses_required_context_precheck(self):
        request = self.factory.get("/subjects/")
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
        middleware = AuthorizationContextMiddleware(lambda request: HttpResponse(status=200))

        response = middleware.process_view(request, decorated_context_view, (), {})

        self.assertIsNone(response)


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "apps.identity.presentation.middleware.AuthorizationContextMiddleware",
    ],
)
class RequireContextPermissionDecoratorTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.client = Client()
        self.user = self._user()
        self.client.force_login(self.user)
        self.study = Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code="STUDY-A",
            name="Study A",
            description="",
            is_active=True,
        )
        self.site = Site.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code="HCM01",
            name="Site HCM01",
            study=self.study,
            is_active=True,
        )
        self.other_study = Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code="STUDY-B",
            name="Study B",
            description="",
            is_active=True,
        )

    @patch("apps.identity.presentation.access.ContextualAuthorizationService")
    def test_decorator_calls_service_with_resolved_context(self, service_class):
        service_class.return_value.can.return_value = AuthorizationDecision(
            allowed=True,
            reason="ALLOWED",
            matched_scope="STUDY_SITE",
            matched_role_id=1,
            permission="datacapture.change_pageentry",
        )

        response = self.client.get(f"/decorated/{self.study.pk}/{self.site.pk}/")

        self.assertEqual(response.status_code, 200)
        service_class.return_value.can.assert_called_once()
        self.assertEqual(service_class.return_value.can.call_args.kwargs["study_id"], self.study.pk)
        self.assertEqual(service_class.return_value.can.call_args.kwargs["study_site_id"], self.site.pk)

    @patch("apps.identity.presentation.access.ContextualAuthorizationService")
    def test_unauthorized_request_returns_403(self, service_class):
        service_class.return_value.can.return_value = AuthorizationDecision(
            allowed=False,
            reason="PERMISSION_NOT_GRANTED",
            matched_scope=None,
            matched_role_id=None,
            permission="datacapture.change_pageentry",
        )

        response = self.client.get(f"/decorated/{self.study.pk}/{self.site.pk}/")

        self.assertEqual(response.status_code, 403)

    @patch("apps.identity.presentation.access.ContextualAuthorizationService")
    def test_malformed_context_returns_400(self, service_class):
        response = self.client.get(f"/decorated/{self.other_study.pk}/{self.site.pk}/")

        self.assertEqual(response.status_code, 400)
        service_class.return_value.can.assert_not_called()

    def test_unauthenticated_request_redirects_to_login(self):
        self.client.logout()

        response = self.client.get(f"/decorated/{self.study.pk}/{self.site.pk}/")

        self.assertEqual(response.status_code, 302)

    @staticmethod
    def _user():
        from apps.identity.models import User

        return User.objects.create_user(username="decorator-user", password="pw")


class AuthorizationContextMiddlewareAnonymousTests(TestCase):
    def test_anonymous_request_keeps_empty_context(self):
        request = RequestFactory().get("/subjects/")
        request.user = AnonymousUser()
        middleware = AuthorizationContextMiddleware(lambda request: HttpResponse(status=200))

        middleware(request)

        self.assertIsNone(request.authorization_context.study_id)
        self.assertIsNone(request.authorization_context.study_site_id)

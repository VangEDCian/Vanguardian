from django.test import SimpleTestCase
from django.urls import Resolver404, resolve, reverse

from apps.identity.presentation.web.views import CurrentUserChangePasswordView, CurrentUserProfileView


class CurrentUserAccountRouteTests(SimpleTestCase):
    def test_profile_route_is_canonical_trailing_slash_view(self):
        self.assertEqual(reverse("identity:current_user_profile"), "/admin/user/me/profile/")

        match = resolve("/admin/user/me/profile/")

        self.assertEqual(match.func.view_class, CurrentUserProfileView)

    def test_legacy_profile_routes_are_removed(self):
        with self.assertRaises(Resolver404):
            resolve("/admin/profile")

        with self.assertRaises(Resolver404):
            resolve("/admin/profile/")

    def test_change_password_route_is_canonical_trailing_slash_view(self):
        self.assertEqual(reverse("identity:current_user_change_password"), "/admin/user/me/change-password/")

        match = resolve("/admin/user/me/change-password/")

        self.assertEqual(match.func.view_class, CurrentUserChangePasswordView)

    def test_legacy_change_password_routes_are_removed(self):
        with self.assertRaises(Resolver404):
            resolve("/admin/change-password")

        with self.assertRaises(Resolver404):
            resolve("/admin/change-password/")

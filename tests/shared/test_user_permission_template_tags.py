from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.identity.application.permissions import ALL_PERMISSION_DEFINITIONS
from apps.shared.templatetags.user_permissions import (
    build_user_permission_flags,
    permission_template_key,
)


class UserPermissionTemplateTagTests(SimpleTestCase):
    def test_subject_list_permission_uses_screen_key(self):
        self.assertEqual(
            permission_template_key("subject.view_subject_list"),
            "SUBJECTS_VIEW_LIST",
        )

    def test_superuser_receives_all_permission_flags(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_superuser=True,
        )

        flags = build_user_permission_flags(user, study_id=1, site_id=2)

        self.assertEqual(len(flags), len(ALL_PERMISSION_DEFINITIONS))
        self.assertTrue(flags["SUBJECTS_VIEW_LIST"])
        self.assertTrue(flags["USERS_VIEW_LIST"])
        self.assertTrue(all(flags.values()))

    @patch("apps.shared.templatetags.user_permissions.ContextualAuthorizationService")
    def test_non_superuser_checks_identity_permission_authorization(self, authorization_service):
        def can(user, permission, **kwargs):
            return SimpleNamespace(allowed=permission == "subject.view_subject_list")

        authorization_service.return_value.can.side_effect = can
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_superuser=False,
        )

        flags = build_user_permission_flags(user, study_id=1, site_id=2)

        self.assertTrue(flags["SUBJECTS_VIEW_LIST"])
        self.assertFalse(flags["USERS_VIEW_LIST"])
        authorization_service.return_value.can.assert_any_call(
            user,
            "subject.view_subject_list",
            study_id=1,
            study_site_id=2,
        )

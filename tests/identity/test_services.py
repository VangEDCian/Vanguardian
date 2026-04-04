from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.identity.application.commands.delete_user import (
    DELETED_USERNAME_PREFIX,
    DeleteIdentityUserCommand,
    DeleteIdentityUserService,
)
from apps.identity.application.queries import IdentityUserNotFoundError


def _make_user(**kwargs):
    defaults = {
        "pk": 1,
        "username": "demo-user",
        "first_name": "Demo",
        "last_name": "User",
        "display_name": "Demo User",
        "email": "demo@example.com",
        "phone_number": "123",
        "is_active": True,
        "is_staff": True,
        "is_superuser": False,
    }
    defaults.update(kwargs)
    user = MagicMock(**defaults)
    user.pk = defaults["pk"]
    user.username = defaults["username"]
    user.first_name = defaults["first_name"]
    user.last_name = defaults["last_name"]
    user.display_name = defaults["display_name"]
    user.email = defaults["email"]
    user.phone_number = defaults["phone_number"]
    user.is_active = defaults["is_active"]
    user.is_staff = defaults["is_staff"]
    user.is_superuser = defaults["is_superuser"]
    user.groups = MagicMock()
    return user


class DeleteIdentityUserServiceTests(SimpleTestCase):
    @patch("apps.identity.application.commands.delete_user.User")
    def test_anonymizes_and_deactivates_user(self, mock_user_cls):
        user = _make_user(pk=7)
        mock_user_cls.objects.filter.return_value.first.return_value = user

        DeleteIdentityUserService().execute(
            DeleteIdentityUserCommand(user_id=7, actor_user_id=1)
        )

        self.assertEqual(user.username, f"{DELETED_USERNAME_PREFIX}7")
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertEqual(user.display_name, "Deleted User")
        self.assertIsNone(user.email)
        self.assertIsNone(user.phone_number)
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        user.save.assert_called_once()
        user.groups.clear.assert_called_once()

    @patch("apps.identity.application.commands.delete_user.User")
    def test_raises_when_user_not_found(self, mock_user_cls):
        mock_user_cls.objects.filter.return_value.first.return_value = None

        with self.assertRaises(IdentityUserNotFoundError):
            DeleteIdentityUserService().execute(
                DeleteIdentityUserCommand(user_id=999, actor_user_id=1)
            )

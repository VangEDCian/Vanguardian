from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.identity.application.commands.delete_user import (
    DeleteIdentityUserCommand,
    DeleteIdentityUserService,
    IdentityUserRestoreDataNotFoundError,
    RestoreIdentityUserCommand,
    RestoreIdentityUserService,
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
        "deleted": False,
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
    user.deleted = defaults["deleted"]
    user.groups = MagicMock()
    return user


class DeleteIdentityUserServiceTests(SimpleTestCase):
    @patch("apps.identity.application.commands.delete_user.User")
    def test_marks_user_deleted_without_overwriting_profile(self, mock_user_cls):
        user = _make_user(pk=7)
        mock_user_cls.objects.prefetch_related.return_value.filter.return_value.first.return_value = user

        DeleteIdentityUserService().execute(
            DeleteIdentityUserCommand(user_id=7, actor_user_id=1)
        )

        self.assertEqual(user.username, "demo-user")
        self.assertEqual(user.first_name, "Demo")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.display_name, "Demo User")
        self.assertEqual(user.email, "demo@example.com")
        self.assertEqual(user.phone_number, "123")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.deleted)
        user.save.assert_called_once()
        user.groups.set.assert_not_called()

    @patch("apps.identity.application.commands.delete_user.User")
    def test_raises_when_user_not_found(self, mock_user_cls):
        mock_user_cls.objects.prefetch_related.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(IdentityUserNotFoundError):
            DeleteIdentityUserService().execute(
                DeleteIdentityUserCommand(user_id=999, actor_user_id=1)
            )


class RestoreIdentityUserServiceTests(SimpleTestCase):
    @patch("apps.identity.application.commands.delete_user.AuditEvent")
    @patch("apps.identity.application.commands.delete_user.User")
    @patch("apps.identity.application.commands.delete_user.Group")
    def test_restores_user_from_latest_deleted_snapshot(self, mock_group_cls, mock_user_cls, mock_audit_event_cls):
        user = _make_user(
            pk=9,
            username="demo-user",
            is_active=False,
            is_staff=False,
            is_superuser=False,
            deleted=True,
        )
        mock_user_cls.objects.prefetch_related.return_value.filter.return_value.first.return_value = user
        mock_user_cls.objects.filter.return_value.exclude.return_value.exists.return_value = False
        mock_group_cls.objects.filter.return_value.order_by.return_value = ["group-a"]

        deleted_event = MagicMock()
        deleted_event.before_data = (
            '{"username": "demo-user", "display_name": "Demo User", "first_name": "Demo", '
            '"last_name": "User", "email": "demo@example.com", "phone_number": "123", '
            '"role_key": "staff", "is_active": true, "permission_groups": ["Investigators"]}'
        )
        mock_audit_event_cls.objects.filter.return_value.order_by.return_value.first.return_value = deleted_event

        restored_user = RestoreIdentityUserService().execute(
            RestoreIdentityUserCommand(user_id=9, actor_user_id=1)
        )

        self.assertEqual(user.username, "demo-user")
        self.assertEqual(user.first_name, "Demo")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.display_name, "Demo User")
        self.assertEqual(user.email, "demo@example.com")
        self.assertEqual(user.phone_number, "123")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.deleted)
        user.save.assert_called_once()
        user.groups.set.assert_called_once_with(["group-a"])
        self.assertIs(restored_user, mock_user_cls.objects.prefetch_related.return_value.get.return_value)

    @patch("apps.identity.application.commands.delete_user.AuditEvent")
    @patch("apps.identity.application.commands.delete_user.User")
    def test_raises_when_restore_snapshot_missing(self, mock_user_cls, mock_audit_event_cls):
        user = _make_user(pk=11, username="demo-user", is_active=False, deleted=True)
        mock_user_cls.objects.prefetch_related.return_value.filter.return_value.first.return_value = user
        mock_audit_event_cls.objects.filter.return_value.order_by.return_value.first.return_value = None

        with self.assertRaises(IdentityUserRestoreDataNotFoundError):
            RestoreIdentityUserService().execute(
                RestoreIdentityUserCommand(user_id=11, actor_user_id=1)
            )

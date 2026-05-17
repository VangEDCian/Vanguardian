from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.identity.application.commands.delete_user import (
    DeleteIdentityUserCommand,
    IdentityUserRestoreDataNotFoundError,
    RestoreIdentityUserCommand,
)
from apps.identity.application.queries import IdentityUserNotFoundError
from apps.identity.application.services import (
    CurrentUserProfileSummaryService,
    DeleteIdentityUserService,
    RestoreIdentityUserService,
)


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
    def test_marks_user_deleted_and_suffixes_unique_identifiers(self):
        user = _make_user(pk=7)
        repository = MagicMock()
        repository.get_user_with_groups.return_value = user
        repository.save_user.side_effect = lambda item: item

        service = DeleteIdentityUserService(repository=repository)

        DeleteIdentityUserService.execute.__wrapped__(
            service,
            DeleteIdentityUserCommand(user_id=7, actor_user_id=1),
        )

        self.assertTrue(user.username.startswith("demo-user_deleted_"))
        self.assertEqual(user.first_name, "Demo")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.display_name, "Demo User")
        self.assertTrue(user.email.startswith("demo@example.com_deleted_"))
        self.assertTrue(user.phone_number.startswith("123_deleted_"))
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.deleted)
        repository.save_user.assert_called_once_with(user)
        user.groups.set.assert_not_called()

    def test_raises_when_user_not_found(self):
        repository = MagicMock()
        repository.get_user_with_groups.return_value = None

        with self.assertRaises(IdentityUserNotFoundError):
            DeleteIdentityUserService.execute.__wrapped__(
                DeleteIdentityUserService(repository=repository),
                DeleteIdentityUserCommand(user_id=999, actor_user_id=1),
            )


class RestoreIdentityUserServiceTests(SimpleTestCase):
    def test_restores_user_from_latest_deleted_snapshot(self):
        user = _make_user(
            pk=9,
            username="demo-user_deleted_deadbeef",
            is_active=False,
            is_staff=False,
            is_superuser=False,
            deleted=True,
        )
        deleted_event = MagicMock()
        deleted_event.before_data = (
            '{"username": "demo-user", "display_name": "Demo User", "first_name": "Demo", '
            '"last_name": "User", "email": "demo@example.com", "phone_number": "123", '
            '"role_key": "staff", "is_active": true, "permission_groups": ["Investigators"]}'
        )

        repository = MagicMock()
        repository.get_user_with_groups.return_value = user
        repository.get_latest_user_deleted_event.return_value = deleted_event
        repository.username_exists.return_value = False
        repository.email_exists.return_value = False
        repository.phone_number_exists.return_value = False
        repository.list_groups_by_names.return_value = ["group-a"]
        repository.reload_user_with_groups.return_value = user

        restored_user = RestoreIdentityUserService.execute.__wrapped__(
            RestoreIdentityUserService(repository=repository),
            RestoreIdentityUserCommand(user_id=9, actor_user_id=1),
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
        repository.save_user.assert_called_once_with(user)
        user.groups.set.assert_called_once_with(["group-a"])
        self.assertIs(restored_user, user)

    def test_raises_when_restore_snapshot_missing(self):
        user = _make_user(pk=11, username="demo-user", is_active=False, deleted=True)
        repository = MagicMock()
        repository.get_user_with_groups.return_value = user
        repository.get_latest_user_deleted_event.return_value = None

        with self.assertRaises(IdentityUserRestoreDataNotFoundError):
            RestoreIdentityUserService.execute.__wrapped__(
                RestoreIdentityUserService(repository=repository),
                RestoreIdentityUserCommand(user_id=11, actor_user_id=1),
            )


class CurrentUserProfileSummaryServiceTests(SimpleTestCase):
    def test_builds_role_label_from_user_role_mappings(self):
        user = _make_user(is_staff=True, is_superuser=False)
        user.get_full_name.return_value = "Demo User"
        user.get_username.return_value = "demo-user"
        user.date_joined = None
        user.last_login = None

        repository = MagicMock()
        repository.list_user_roles.return_value = [
            SimpleNamespace(role=SimpleNamespace(name="Coordinator")),
            SimpleNamespace(role=SimpleNamespace(name="Investigator")),
        ]

        summary = CurrentUserProfileSummaryService(repository=repository).build(user)

        self.assertEqual(summary["role_label"], "Coordinator, Investigator")
        self.assertFalse(summary["is_superuser"])
        self.assertTrue(summary["is_staff"])
        self.assertTrue(summary["is_active"])
        self.assertEqual(summary["administrator_label"], "Administrator")
        self.assertEqual(summary["staff_label"], "Staff")
        repository.list_user_roles.assert_called_once_with(user)

    def test_uses_placeholder_when_user_has_no_role_mappings(self):
        user = _make_user(is_staff=False, is_superuser=False)
        user.get_full_name.return_value = ""
        user.get_username.return_value = "demo-user"
        user.date_joined = None
        user.last_login = None

        repository = MagicMock()
        repository.list_user_roles.return_value = []

        summary = CurrentUserProfileSummaryService(repository=repository).build(user)

        self.assertEqual(summary["display_name"], "Demo User")
        self.assertEqual(summary["role_label"], "—")

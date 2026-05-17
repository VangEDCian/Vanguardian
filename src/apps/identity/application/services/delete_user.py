import json

from django.db import transaction

from apps.identity.application.commands.delete_user import (
    DeleteIdentityUserCommand,
    IdentityUserRestoreDataNotFoundError,
    RestoreIdentityUserCommand,
)
from apps.identity.application.queries import IdentityUserNotFoundError
from apps.identity.infrastructure.repositories import DjangoIdentityUserRepository
from apps.shared.application.services.soft_delete import (
    build_soft_deleted_optional_unique_value,
    build_soft_deleted_unique_value,
)


class DeleteIdentityUserService:
    repository_class = DjangoIdentityUserRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: DeleteIdentityUserCommand) -> None:
        user = self.repository.get_user_with_groups(user_id=command.user_id)
        if user is None:
            raise IdentityUserNotFoundError(command.user_id)

        user.username = build_soft_deleted_unique_value(user.username)
        user.email = build_soft_deleted_optional_unique_value(user.email)
        user.phone_number = build_soft_deleted_optional_unique_value(user.phone_number)
        user.deleted = True
        user.is_active = False
        user.is_staff = False
        user.is_superuser = False
        self.repository.save_user(user)


class RestoreIdentityUserService:
    repository_class = DjangoIdentityUserRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: RestoreIdentityUserCommand):
        user = self.repository.get_user_with_groups(user_id=command.user_id)
        if user is None:
            raise IdentityUserNotFoundError(command.user_id)

        snapshot = self._load_deleted_snapshot(user.pk)

        restored_username = (snapshot.get("username") or "").strip()
        restored_email = self._normalize_optional_identifier(snapshot.get("email"))
        restored_phone_number = self._normalize_optional_identifier(snapshot.get("phone_number"))

        self._validate_unique_username(restored_username, exclude_user_id=user.pk)
        self._validate_unique_email(restored_email, exclude_user_id=user.pk)
        self._validate_unique_phone_number(restored_phone_number, exclude_user_id=user.pk)

        if restored_username:
            user.username = restored_username
        user.first_name = (snapshot.get("first_name") or "").strip()
        user.last_name = (snapshot.get("last_name") or "").strip()
        user.display_name = (snapshot.get("display_name") or "").strip()
        user.email = restored_email
        user.phone_number = restored_phone_number
        user.deleted = False
        user.is_active = bool(snapshot.get("is_active", True))
        self._apply_role_flags(user, snapshot.get("role_key"))
        self.repository.save_user(user)

        restored_group_names = [
            group_name
            for group_name in snapshot.get("permission_groups", [])
            if group_name
        ]
        user.groups.set(self.repository.list_groups_by_names(restored_group_names))

        return self.repository.reload_user_with_groups(user)

    def _load_deleted_snapshot(self, user_id):
        deleted_event = self.repository.get_latest_user_deleted_event(user_id=user_id)
        if deleted_event is None:
            raise IdentityUserRestoreDataNotFoundError(user_id)

        try:
            snapshot = json.loads(deleted_event.before_data or "{}")
        except json.JSONDecodeError as exc:
            raise IdentityUserRestoreDataNotFoundError(user_id) from exc

        if not isinstance(snapshot, dict) or not snapshot:
            raise IdentityUserRestoreDataNotFoundError(user_id)
        return snapshot

    @staticmethod
    def _normalize_optional_identifier(value):
        if value is None:
            return None

        normalized_value = str(value).strip()
        return normalized_value or None

    def _validate_unique_username(self, username, *, exclude_user_id):
        if not username:
            return

        if self.repository.username_exists(username=username, exclude_user_id=exclude_user_id, deleted=False):
            raise IdentityUserRestoreDataNotFoundError(username)

    def _validate_unique_email(self, email, *, exclude_user_id):
        if not email:
            return

        if self.repository.email_exists(email=email, exclude_user_id=exclude_user_id, deleted=False):
            raise IdentityUserRestoreDataNotFoundError(email)

    def _validate_unique_phone_number(self, phone_number, *, exclude_user_id):
        if not phone_number:
            return

        if self.repository.phone_number_exists(
            phone_number=phone_number,
            exclude_user_id=exclude_user_id,
            deleted=False,
        ):
            raise IdentityUserRestoreDataNotFoundError(phone_number)

    @staticmethod
    def _apply_role_flags(user, role_key):
        normalized_role_key = (role_key or "user").strip().lower()
        if normalized_role_key == "administrator":
            user.is_superuser = True
            user.is_staff = True
            return

        if normalized_role_key == "staff":
            user.is_superuser = False
            user.is_staff = True
            return

        user.is_superuser = False
        user.is_staff = False


__all__ = [
    "DeleteIdentityUserService",
    "RestoreIdentityUserService",
]

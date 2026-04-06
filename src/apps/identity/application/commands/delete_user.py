import json
from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.db import transaction

from apps.audit.infrastructure.persistence.models import AuditEvent
from apps.identity.application.queries import IdentityUserNotFoundError
from apps.identity.models import User
from apps.shared.constants import AuditEventAction, AuditEventObjectType


@dataclass(frozen=True)
class DeleteIdentityUserCommand:
    user_id: int
    actor_user_id: int


@dataclass(frozen=True)
class RestoreIdentityUserCommand:
    user_id: int
    actor_user_id: int


class IdentityUserRestoreDataNotFoundError(Exception):
    pass


class DeleteIdentityUserService:
    @transaction.atomic
    def execute(self, command: DeleteIdentityUserCommand) -> None:
        user = User.objects.prefetch_related("groups").filter(pk=command.user_id).first()
        if user is None:
            raise IdentityUserNotFoundError(command.user_id)

        user.deleted = True
        user.is_active = False
        user.is_staff = False
        user.is_superuser = False
        user.save()


class RestoreIdentityUserService:
    @transaction.atomic
    def execute(self, command: RestoreIdentityUserCommand) -> User:
        user = User.objects.prefetch_related("groups").filter(pk=command.user_id).first()
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
        user.save()

        restored_group_names = [
            group_name
            for group_name in snapshot.get("permission_groups", [])
            if group_name
        ]
        user.groups.set(Group.objects.filter(name__in=restored_group_names).order_by("name"))

        return User.objects.prefetch_related("groups").get(pk=user.pk)

    @staticmethod
    def _load_deleted_snapshot(user_id):
        deleted_event = AuditEvent.objects.filter(
            deleted=False,
            action=AuditEventAction.IDENTITY_USER_DELETED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user_id),
        ).order_by("-created_at").first()
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

    @staticmethod
    def _validate_unique_username(username, *, exclude_user_id):
        if not username:
            return

        if User.objects.filter(username__iexact=username, deleted=False).exclude(pk=exclude_user_id).exists():
            raise IdentityUserRestoreDataNotFoundError(username)

    @staticmethod
    def _validate_unique_email(email, *, exclude_user_id):
        if not email:
            return

        if User.objects.filter(email__iexact=email, deleted=False).exclude(pk=exclude_user_id).exists():
            raise IdentityUserRestoreDataNotFoundError(email)

    @staticmethod
    def _validate_unique_phone_number(phone_number, *, exclude_user_id):
        if not phone_number:
            return

        if User.objects.filter(phone_number=phone_number, deleted=False).exclude(pk=exclude_user_id).exists():
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

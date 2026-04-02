from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.db import transaction

from apps.identity.application.commands.update_user_detail import (
    IdentityUserEmailAlreadyExistsError,
    IdentityUserPhoneNumberAlreadyExistsError,
)
from apps.identity.models import User


class IdentityUsernameAlreadyExistsError(Exception):
    pass


@dataclass(frozen=True)
class CreateIdentityUserCommand:
    actor_user_id: int
    username: str
    password: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    role_key: str = "user"
    permission_group_ids: tuple[str, ...] = ()
    can_manage_permissions: bool = False


class CreateIdentityUserService:
    @transaction.atomic
    def execute(self, command: CreateIdentityUserCommand) -> User:
        normalized_username = (command.username or "").strip()
        normalized_email = self._normalize_optional_identifier(command.email)
        normalized_phone_number = self._normalize_optional_identifier(command.phone_number)

        self._validate_unique_username(normalized_username)
        self._validate_unique_email(normalized_email)
        self._validate_unique_phone_number(normalized_phone_number)

        user = User(
            username=normalized_username,
            first_name=(command.first_name or "").strip(),
            last_name=(command.last_name or "").strip(),
            email=normalized_email,
            phone_number=normalized_phone_number,
            display_name="",
        )
        user.set_password(command.password)

        if command.can_manage_permissions:
            self._apply_role_flags(user, command.role_key)

        user.save()

        if command.can_manage_permissions:
            user.groups.set(self._resolve_groups(command.permission_group_ids))

        return User.objects.prefetch_related("groups").get(pk=user.pk)

    @staticmethod
    def _normalize_optional_identifier(value):
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @staticmethod
    def _validate_unique_username(username):
        if not username:
            return

        if User.objects.filter(username__iexact=username).exists():
            raise IdentityUsernameAlreadyExistsError(username)

    @staticmethod
    def _validate_unique_email(email):
        if not email:
            return

        if User.objects.filter(email__iexact=email).exists():
            raise IdentityUserEmailAlreadyExistsError(email)

    @staticmethod
    def _validate_unique_phone_number(phone_number):
        if not phone_number:
            return

        if User.objects.filter(phone_number=phone_number).exists():
            raise IdentityUserPhoneNumberAlreadyExistsError(phone_number)

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

    @staticmethod
    def _resolve_groups(permission_group_ids):
        normalized_group_ids = []
        seen_group_ids = set()
        for permission_group_id in permission_group_ids or ():
            normalized_group_id = str(permission_group_id).strip()
            if not normalized_group_id or normalized_group_id in seen_group_ids:
                continue
            seen_group_ids.add(normalized_group_id)
            normalized_group_ids.append(normalized_group_id)

        return Group.objects.filter(pk__in=normalized_group_ids).order_by("name")

from django.db import transaction

from apps.identity.application.commands.update_user_detail import (
    IdentityUserEmailAlreadyExistsError,
    IdentityUserPhoneNumberAlreadyExistsError,
    UpdateIdentityUserDetailCommand,
)
from apps.identity.application.queries import IdentityUserNotFoundError
from apps.identity.infrastructure.repositories import DjangoIdentityUserRepository


class UpdateIdentityUserDetailService:
    repository_class = DjangoIdentityUserRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: UpdateIdentityUserDetailCommand):
        user = self.repository.get_user_with_groups(user_id=command.user_id)
        if user is None:
            raise IdentityUserNotFoundError(command.user_id)

        normalized_email = self._normalize_optional_identifier(command.email)
        normalized_phone_number = self._normalize_optional_identifier(command.phone_number)

        self._validate_unique_email(normalized_email, exclude_user_id=user.pk)
        self._validate_unique_phone_number(normalized_phone_number, exclude_user_id=user.pk)

        user.first_name = (command.first_name or "").strip()
        user.last_name = (command.last_name or "").strip()
        user.email = normalized_email
        user.phone_number = normalized_phone_number
        user.is_active = bool(command.is_active)

        if command.can_manage_permissions:
            self._apply_role_flags(user, command.role_key)

        if command.new_password:
            user.set_password(command.new_password)
            user.attempt_login = 0

        self.repository.save_user(user)

        if command.can_manage_permissions:
            user.groups.set(self._resolve_groups(command.permission_group_ids))

        return self.repository.reload_user_with_groups(user)

    @staticmethod
    def _normalize_optional_identifier(value):
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    def _validate_unique_email(self, email, *, exclude_user_id):
        if not email:
            return

        if self.repository.email_exists(email=email, exclude_user_id=exclude_user_id):
            raise IdentityUserEmailAlreadyExistsError(email)

    def _validate_unique_phone_number(self, phone_number, *, exclude_user_id):
        if not phone_number:
            return

        if self.repository.phone_number_exists(phone_number=phone_number, exclude_user_id=exclude_user_id):
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

    def _resolve_groups(self, permission_group_ids):
        normalized_group_ids = []
        seen_group_ids = set()
        for permission_group_id in permission_group_ids or ():
            normalized_group_id = str(permission_group_id).strip()
            if not normalized_group_id or normalized_group_id in seen_group_ids:
                continue
            seen_group_ids.add(normalized_group_id)
            normalized_group_ids.append(normalized_group_id)

        return self.repository.list_groups_by_ids(normalized_group_ids)


__all__ = ["UpdateIdentityUserDetailService"]

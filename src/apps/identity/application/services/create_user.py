from django.db import transaction

from apps.identity.application.commands.create_user import (
    CreateIdentityUserCommand,
    IdentityUsernameAlreadyExistsError,
)
from apps.identity.application.commands.update_user_detail import (
    IdentityUserEmailAlreadyExistsError,
    IdentityUserPhoneNumberAlreadyExistsError,
)
from apps.identity.infrastructure.repositories import DjangoIdentityUserRepository


class CreateIdentityUserService:
    repository_class = DjangoIdentityUserRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: CreateIdentityUserCommand):
        normalized_username = (command.username or "").strip()
        normalized_email = self._normalize_optional_identifier(command.email)
        normalized_phone_number = self._normalize_optional_identifier(command.phone_number)

        self._validate_unique_username(normalized_username)
        self._validate_unique_email(normalized_email)
        self._validate_unique_phone_number(normalized_phone_number)

        user = self.repository.build_user(
            username=normalized_username,
            first_name=(command.first_name or "").strip(),
            last_name=(command.last_name or "").strip(),
            email=normalized_email,
            phone_number=normalized_phone_number,
            display_name="",
        )
        user.set_password(command.password)

        self.repository.save_user(user)

        if command.can_manage_permissions:
            self.repository.clear_user_roles(user=user)
            self.repository.set_user_study_memberships(
                user=user,
                study_ids=command.study_ids,
                actor_user_id=command.actor_user_id,
                role_ids_by_study_id=command.study_role_ids_by_study_id,
            )
            self.repository.set_user_site_memberships(
                user=user,
                site_ids=command.site_ids,
                allowed_study_ids=command.study_ids,
                actor_user_id=command.actor_user_id,
                role_ids_by_site_id=command.site_role_ids_by_site_id,
            )

        if command.can_manage_permissions:
            user.groups.set(self._resolve_groups(command.permission_group_ids))

        return self.repository.reload_user_with_groups(user)

    @staticmethod
    def _normalize_optional_identifier(value):
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    def _validate_unique_username(self, username):
        if not username:
            return

        if self.repository.username_exists(username=username):
            raise IdentityUsernameAlreadyExistsError(username)

    def _validate_unique_email(self, email):
        if not email:
            return

        if self.repository.email_exists(email=email):
            raise IdentityUserEmailAlreadyExistsError(email)

    def _validate_unique_phone_number(self, phone_number):
        if not phone_number:
            return

        if self.repository.phone_number_exists(phone_number=phone_number):
            raise IdentityUserPhoneNumberAlreadyExistsError(phone_number)

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


__all__ = ["CreateIdentityUserService"]

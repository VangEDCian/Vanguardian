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
        user = self.repository.get_user(user_id=command.user_id)
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

        if command.new_password:
            user.set_password(command.new_password)
            user.attempt_login = 0

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

        return self.repository.reload_user(user)

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

__all__ = ["UpdateIdentityUserDetailService"]

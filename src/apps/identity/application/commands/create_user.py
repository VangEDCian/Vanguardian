from dataclasses import dataclass

from apps.identity.application.commands.update_user_detail import (
    IdentityUserEmailAlreadyExistsError,
    IdentityUserPhoneNumberAlreadyExistsError,
)


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
    role_id: str = ""
    study_ids: tuple[str, ...] = ()
    site_ids: tuple[str, ...] = ()
    permission_group_ids: tuple[str, ...] = ()
    can_manage_permissions: bool = False

__all__ = [
    "CreateIdentityUserCommand",
    "IdentityUserEmailAlreadyExistsError",
    "IdentityUserPhoneNumberAlreadyExistsError",
    "IdentityUsernameAlreadyExistsError",
]

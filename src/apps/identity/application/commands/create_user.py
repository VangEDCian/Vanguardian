from dataclasses import dataclass

from apps.identity.application.exceptions import (
    IdentityUserEmailAlreadyExistsError,
    IdentityUsernameAlreadyExistsError,
    IdentityUserPhoneNumberAlreadyExistsError,
)


@dataclass(frozen=True)
class CreateIdentityUserCommand:
    actor_user_id: int
    username: str
    password: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    study_ids: tuple[str, ...] = ()
    site_ids: tuple[str, ...] = ()
    study_role_ids_by_study_id: dict[str, str] | None = None
    site_role_ids_by_site_id: dict[str, str] | None = None
    can_manage_permissions: bool = False

__all__ = [
    "CreateIdentityUserCommand",
    "IdentityUserEmailAlreadyExistsError",
    "IdentityUserPhoneNumberAlreadyExistsError",
    "IdentityUsernameAlreadyExistsError",
]

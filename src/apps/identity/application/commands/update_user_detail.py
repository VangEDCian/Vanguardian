from dataclasses import dataclass

from apps.identity.application.exceptions import (
    IdentityUserEmailAlreadyExistsError,
    IdentityUserPhoneNumberAlreadyExistsError,
)


@dataclass(frozen=True)
class UpdateIdentityUserDetailCommand:
    user_id: int
    actor_user_id: int
    first_name: str
    last_name: str
    email: str
    phone_number: str
    is_active: bool
    role_id: str = ""
    study_ids: tuple[str, ...] = ()
    site_ids: tuple[str, ...] = ()
    permission_group_ids: tuple[str, ...] = ()
    can_manage_permissions: bool = False
    new_password: str | None = None

__all__ = [
    "IdentityUserEmailAlreadyExistsError",
    "IdentityUserPhoneNumberAlreadyExistsError",
    "UpdateIdentityUserDetailCommand",
]

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
    study_ids: tuple[str, ...] = ()
    site_ids: tuple[str, ...] = ()
    study_role_ids_by_study_id: dict[str, str] | None = None
    site_role_ids_by_site_id: dict[str, str] | None = None
    can_manage_permissions: bool = False
    new_password: str | None = None

__all__ = [
    "IdentityUserEmailAlreadyExistsError",
    "IdentityUserPhoneNumberAlreadyExistsError",
    "UpdateIdentityUserDetailCommand",
]

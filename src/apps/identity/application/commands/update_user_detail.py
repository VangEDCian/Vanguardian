from dataclasses import dataclass


class IdentityUserEmailAlreadyExistsError(Exception):
    pass


class IdentityUserPhoneNumberAlreadyExistsError(Exception):
    pass


@dataclass(frozen=True)
class UpdateIdentityUserDetailCommand:
    user_id: int
    actor_user_id: int
    first_name: str
    last_name: str
    email: str
    phone_number: str
    is_active: bool
    role_key: str = "user"
    permission_group_ids: tuple[str, ...] = ()
    can_manage_permissions: bool = False
    new_password: str | None = None

__all__ = [
    "IdentityUserEmailAlreadyExistsError",
    "IdentityUserPhoneNumberAlreadyExistsError",
    "UpdateIdentityUserDetailCommand",
]

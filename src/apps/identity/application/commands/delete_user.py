from dataclasses import dataclass

from apps.identity.application.exceptions import IdentityUserRestoreDataNotFoundError


@dataclass(frozen=True)
class DeleteIdentityUserCommand:
    user_id: int
    actor_user_id: int


@dataclass(frozen=True)
class RestoreIdentityUserCommand:
    user_id: int
    actor_user_id: int


__all__ = [
    "DeleteIdentityUserCommand",
    "IdentityUserRestoreDataNotFoundError",
    "RestoreIdentityUserCommand",
]

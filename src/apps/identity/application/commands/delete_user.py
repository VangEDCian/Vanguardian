from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteIdentityUserCommand:
    user_id: int
    actor_user_id: int


@dataclass(frozen=True)
class RestoreIdentityUserCommand:
    user_id: int
    actor_user_id: int


class IdentityUserRestoreDataNotFoundError(Exception):
    pass

__all__ = [
    "DeleteIdentityUserCommand",
    "IdentityUserRestoreDataNotFoundError",
    "RestoreIdentityUserCommand",
]

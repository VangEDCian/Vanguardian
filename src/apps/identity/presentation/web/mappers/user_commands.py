from apps.identity.application import (
    CreateIdentityUserCommand,
    DeleteIdentityUserCommand,
    RestoreIdentityUserCommand,
    UpdateIdentityUserDetailCommand,
)


def to_create_identity_user_command(**kwargs) -> CreateIdentityUserCommand:
    return CreateIdentityUserCommand(**kwargs)


def to_update_identity_user_detail_command(**kwargs) -> UpdateIdentityUserDetailCommand:
    return UpdateIdentityUserDetailCommand(**kwargs)


def to_delete_identity_user_command(**kwargs) -> DeleteIdentityUserCommand:
    return DeleteIdentityUserCommand(**kwargs)


def to_restore_identity_user_command(**kwargs) -> RestoreIdentityUserCommand:
    return RestoreIdentityUserCommand(**kwargs)


__all__ = [
    "to_create_identity_user_command",
    "to_update_identity_user_detail_command",
    "to_delete_identity_user_command",
    "to_restore_identity_user_command",
]

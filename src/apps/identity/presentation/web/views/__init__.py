from apps.identity.presentation.web.views.auth import (
    IdentityLoginView,
    IdentityLogoutView,
    IdentityUserFirstLoginView,
)
from apps.identity.presentation.web.views.users import (
    IdentityUserCreateView,
    IdentityUserDeleteView,
    IdentityUserDetailView,
    IdentityUserRestoreView,
    IdentityUsersView,
    target_user_role_key,
)

__all__ = [
    "IdentityLoginView",
    "IdentityLogoutView",
    "IdentityUserCreateView",
    "IdentityUserDeleteView",
    "IdentityUserDetailView",
    "IdentityUserFirstLoginView",
    "IdentityUserRestoreView",
    "IdentityUsersView",
    "target_user_role_key",
]

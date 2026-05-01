from apps.identity.presentation.web.views.auth import (
    IdentityForgotPasswordView,
    IdentityLoginView,
    IdentityLogoutView,
    IdentityResetPasswordConfirmView,
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
    "IdentityForgotPasswordView",
    "IdentityLoginView",
    "IdentityLogoutView",
    "IdentityResetPasswordConfirmView",
    "IdentityUserCreateView",
    "IdentityUserDeleteView",
    "IdentityUserDetailView",
    "IdentityUserFirstLoginView",
    "IdentityUserRestoreView",
    "IdentityUsersView",
    "target_user_role_key",
]

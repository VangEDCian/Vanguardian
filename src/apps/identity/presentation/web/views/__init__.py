from apps.identity.presentation.web.views.account import (
    CurrentUserChangePasswordView,
    CurrentUserProfileView,
)
from apps.identity.presentation.web.views.auth import (
    IdentityForgotPasswordView,
    IdentityLoginView,
    IdentityLogoutView,
    IdentityResetPasswordConfirmView,
    IdentityUserFirstLoginView,
)
from apps.identity.presentation.web.views.users import (
    IdentityStudyOptionsApiView,
    IdentityStudySiteOptionsApiView,
    IdentityUserCreateView,
    IdentityUserDeleteView,
    IdentityUserDetailView,
    IdentityUserRestoreView,
    IdentityUsersView,
)

__all__ = [
    "CurrentUserChangePasswordView",
    "CurrentUserProfileView",
    "IdentityForgotPasswordView",
    "IdentityLoginView",
    "IdentityLogoutView",
    "IdentityResetPasswordConfirmView",
    "IdentityStudyOptionsApiView",
    "IdentityStudySiteOptionsApiView",
    "IdentityUserCreateView",
    "IdentityUserDeleteView",
    "IdentityUserDetailView",
    "IdentityUserFirstLoginView",
    "IdentityUserRestoreView",
    "IdentityUsersView",
]

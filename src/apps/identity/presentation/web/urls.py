from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from apps.identity.presentation.web.views import (
    CurrentUserChangePasswordView,
    CurrentUserProfileView,
    IdentityForgotPasswordView,
    IdentityLoginView,
    IdentityLogoutView,
    IdentityResetPasswordConfirmView,
    IdentitySessionStatusView,
    IdentityStudyOptionsApiView,
    IdentityStudySiteOptionsApiView,
    IdentityUserCreateView,
    IdentityUserDeleteView,
    IdentityUserDetailView,
    IdentityUserFirstLoginView,
    IdentityUserRestoreView,
    IdentityUsersView,
)

app_name = "identity"


urlpatterns = [
    path("login/", IdentityLoginView.as_view(), name="login"),
    path(
        "itsnotasignin/",
        RedirectView.as_view(url="/login/", permanent=True, query_string=True),
        name="legacy_login",
    ),
    path("logout/", IdentityLogoutView.as_view(), name="logout"),
    path(
        "admin/user/me/profile/",
        CurrentUserProfileView.as_view(),
        name="current_user_profile",
    ),
    path(
        "admin/user/me/change-password/",
        CurrentUserChangePasswordView.as_view(),
        name="current_user_change_password",
    ),
    path("users", IdentityUsersView.as_view(), name="users"),
    path("users/create", IdentityUserCreateView.as_view(), name="user_create"),
    path("users/<int:user_id>", IdentityUserDetailView.as_view(), name="user_detail"),
    path("users/<int:user_id>/delete", IdentityUserDeleteView.as_view(), name="user_delete"),
    path("users/<int:user_id>/restore", IdentityUserRestoreView.as_view(), name="user_restore"),
    path("api/studies", IdentityStudyOptionsApiView.as_view(), name="api_studies"),
    path("api/studies/sites", IdentityStudySiteOptionsApiView.as_view(), name="api_study_sites"),
    path("api/session/status", IdentitySessionStatusView.as_view(), name="api_session_status"),
    path(
        "first-login",
        IdentityUserFirstLoginView.as_view(), name="first_login",
    ),
    path(
        "forgot-password/",
        IdentityForgotPasswordView.as_view(),
        name="forgot_password",
    ),
    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="identity/forgot_password_done.html",
        ),
        name="forgot_password_done",
    ),
    path(
        "reset-password/<uidb64>/<token>/",
        IdentityResetPasswordConfirmView.as_view(),
        name="reset_password",
    ),
    path(
        "reset-password/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="identity/reset_password_done.html",
        ),
        name="reset_password_done",
    ),
]

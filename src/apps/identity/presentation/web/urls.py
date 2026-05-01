from django.contrib.auth import views as auth_views
from django.urls import path

from apps.identity.presentation.web.views import (
    IdentityForgotPasswordView,
    IdentityLoginView,
    IdentityLogoutView,
    IdentityResetPasswordConfirmView,
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
    path("logout/", IdentityLogoutView.as_view(), name="logout"),
    path("users", IdentityUsersView.as_view(), name="users"),
    path("users/create", IdentityUserCreateView.as_view(), name="user_create"),
    path("users/<int:user_id>", IdentityUserDetailView.as_view(), name="user_detail"),
    path("users/<int:user_id>/delete", IdentityUserDeleteView.as_view(), name="user_delete"),
    path("users/<int:user_id>/restore", IdentityUserRestoreView.as_view(), name="user_restore"),
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

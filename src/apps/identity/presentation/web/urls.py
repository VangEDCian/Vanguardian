from django.contrib.auth import views as auth_views
from django.urls import path

from apps.identity.presentation.web.forms import (
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from apps.identity.presentation.web.views import (
    IdentityLoginView,
    IdentityLogoutView,
    IdentityUserCreateView,
    IdentityUserDeleteView,
    IdentityUserDetailView,
    IdentityUserRestoreView,
    IdentityUsersView,
    IdentityUserChangePasswordView,
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
        "change-password",
        IdentityUserChangePasswordView.as_view(), name="change_password",
    ),
    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            template_name="identity/forgot_password.html",
            email_template_name="identity/password_reset_email.txt",
            subject_template_name="identity/password_reset_subject.txt",
            form_class=StyledPasswordResetForm,
            success_url="/forgot-password/done/",
        ),
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
        auth_views.PasswordResetConfirmView.as_view(
            template_name="identity/reset_password.html",
            form_class=StyledSetPasswordForm,
            success_url="/reset-password/done/",
        ),
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

from typing import Any, cast

from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.views import LoginView, PasswordResetConfirmView, PasswordResetView
from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from apps.audit.public import build_audit_request_context
from apps.identity.application import IdentityLoginAuditService, IdentityUserAuditService
from apps.identity.infrastructure.auth.constants import PASSWORD_RESET_BYPASS_SESSION_KEY
from apps.identity.models import User
from apps.identity.presentation.web.forms import (
    IdentityUserChangePasswordForm,
    StyledAuthenticationForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from apps.shared.application.services.cookies import CookiesService


class IdentityLoginView(LoginView):
    template_name = "identity/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard:main")
    login_audit_service_class = IdentityLoginAuditService

    def get_login_audit_service(self):
        return self.login_audit_service_class()

    def form_valid(self, form: StyledAuthenticationForm):
        response = super().form_valid(form)

        # Any fix typehints | always return user object.
        authenticated_user: User | None | Any = form.get_user()

        # log
        self.get_login_audit_service().record_login_succeeded(
            user=authenticated_user,
            identifier=self._get_login_identifier(),
            **build_audit_request_context(
                self.request,
                actor_user_id=getattr(authenticated_user, "pk", None),
            ),
        )

        # check must be User Object ** has attempt_login and method save
        if (
                authenticated_user
                and hasattr(authenticated_user, 'attempt_login')
                and hasattr(authenticated_user, 'save')
        ):
            # check first-login
            if authenticated_user.attempt_login <= 0:
                if not self._can_skip_first_login(authenticated_user):
                    return redirect(reverse('identity:first_login'))
            else:
                # increase attempt login number
                authenticated_user.attempt_login = F('attempt_login') + 1
                authenticated_user.save(update_fields=['attempt_login'])

            # clear outdate cookies value if exists
            CookiesService.reset_cookies(response=response)

            # goto home
            return response

        # except goto logout
        return redirect(reverse('identity:logout'))

    def form_invalid(self, form):
        self.get_login_audit_service().record_login_failed(
            identifier=self._get_login_identifier(),
            form_errors=form.errors.get_json_data(),
            **build_audit_request_context(self.request),
        )
        return super().form_invalid(form)

    def _get_login_identifier(self):
        return (self.request.POST.get("username") or "").strip()

    def _can_skip_first_login(self, user):
        if not user or not getattr(user, "pk", None):
            return False
        session = getattr(self.request, "session", {})
        bypass_user_ids = set(session.get(PASSWORD_RESET_BYPASS_SESSION_KEY, []))
        return str(user.pk) in bypass_user_ids


class IdentityLogoutView(View):
    def get(self, request, *args, **kwargs):
        if hasattr(request, "session"):
            request.session.pop(PASSWORD_RESET_BYPASS_SESSION_KEY, None)
        logout(request)
        return redirect("identity:login")

    def post(self, request, *args, **kwargs):
        response = self.get(request, *args, **kwargs)
        if hasattr(request, "session"):
            request.session.pop(PASSWORD_RESET_BYPASS_SESSION_KEY, None)
        CookiesService.reset_cookies(response=response)
        return response


class IdentityForgotPasswordView(PasswordResetView):
    template_name = "identity/forgot_password.html"
    email_template_name = "identity/password_reset_email.txt"
    html_email_template_name = "identity/password_reset_email.html"
    subject_template_name = "identity/password_reset_subject.txt"
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy("identity:forgot_password_done")
    extra_email_context = {
        "system_name": "Vanguardian",
    }


class IdentityResetPasswordConfirmView(PasswordResetConfirmView):
    template_name = "identity/reset_password.html"
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy("identity:login")
    identity_user_audit_service_class = IdentityUserAuditService

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def form_valid(self, form: StyledSetPasswordForm):
        user = form.user
        response = super().form_valid(form)

        if hasattr(self.request, "session"):
            bypass_user_ids = set(self.request.session.get(PASSWORD_RESET_BYPASS_SESSION_KEY, []))
            bypass_user_ids.add(str(user.pk))
            self.request.session[PASSWORD_RESET_BYPASS_SESSION_KEY] = sorted(bypass_user_ids)
            self.request.session.modified = True
        self.get_identity_user_audit_service().record_user_reset_password(
            user=user,
            **build_audit_request_context(self.request),
        )
        return response


class IdentityUserFirstLoginView(TemplateView):
    template_name = "identity/first_login.html"
    success_url = reverse_lazy("dashboard:main")

    def dispatch(self, request, *args, **kwargs):
        current_user = cast(User, self.request.user)
        if current_user and current_user.is_authenticated:
            if current_user.attempt_login > 0:
                return redirect(reverse('dashboard:main'))
            return super().dispatch(request, *args, **kwargs)
        return redirect(reverse('identity:login'))

    def get_account_identity(self):
        current_user = cast(User, self.request.user)
        return (
            (getattr(current_user, "display_name", "") or "").strip()
            or (current_user.get_username() or "").strip()
            or (getattr(current_user, "email", "") or "").strip()
            or str(current_user.pk)
        )

    def get_first_login_form(self, *args, **kwargs):
        kwargs.setdefault("user", self.request.user)
        return IdentityUserChangePasswordForm(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", self.get_first_login_form())
        context["account_identity"] = self.get_account_identity()
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_first_login_form(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # force save to db
        request.user.set_password(form.cleaned_data["new_password"])
        update_fields = ["password"]

        # Mark first-login password change as completed.
        if hasattr(request.user, "attempt_login"):
            request.user.attempt_login = max(getattr(request.user, "attempt_login", 0), 1)
            update_fields.append("attempt_login")

        request.user.save(update_fields=update_fields)

        # update session auth hash
        update_session_auth_hash(request, request.user)

        # audit log
        IdentityUserAuditService().record_user_change_password(
            user=request.user,
            **build_audit_request_context(request),
        )

        return redirect(str(self.success_url))

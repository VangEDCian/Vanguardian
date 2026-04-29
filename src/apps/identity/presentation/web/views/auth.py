from typing import Any, cast

from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from apps.audit.public import build_audit_request_context
from apps.identity.application import IdentityLoginAuditService, IdentityUserAuditService
from apps.identity.models import User
from apps.identity.presentation.web.forms import (
    IdentityUserChangePasswordForm,
    StyledAuthenticationForm,
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
                return redirect(reverse('identity:first_login'))

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


class IdentityLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("identity:login")

    def post(self, request, *args, **kwargs):
        response = self.get(request, *args, **kwargs)
        CookiesService.reset_cookies(response=response)
        return response

class IdentityUserFirstLoginView(LoginRequiredMixin, TemplateView):
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

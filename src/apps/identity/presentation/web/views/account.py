from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.audit.public import build_audit_request_context
from apps.identity.application import (
    CurrentUserProfileSummaryService,
    IdentityUserAuditService,
    serialize_identity_user_snapshot,
)
from apps.identity.presentation.web.forms import (
    CurrentUserChangePasswordForm,
    CurrentUserProfileForm,
)
from apps.shared.views.generic import AuthenticateTemplateView


class CurrentUserProfileView(AuthenticateTemplateView):
    template_name = "identity/admin/profile.html"
    layout_nav_key = "ADMIN_PROFILE"
    profile_form_class = CurrentUserProfileForm
    profile_summary_service_class = CurrentUserProfileSummaryService
    identity_user_audit_service_class = IdentityUserAuditService

    def get_profile_form(self, *args, **kwargs):
        kwargs.setdefault("user", self.request.user)
        return self.profile_form_class(*args, **kwargs)

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def get_profile_summary_service(self):
        return self.profile_summary_service_class()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", self.get_profile_form(initial=self._build_profile_initial_data()))
        context["active_admin_section"] = "profile"
        context["admin_back_url"] = reverse("dashboard:main")
        context["profile_summary"] = self._build_profile_summary()
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_profile_form(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        before_data = serialize_identity_user_snapshot(request.user)
        request.user.display_name = form.cleaned_data["display_name"]
        request.user.first_name = form.cleaned_data["first_name"]
        request.user.last_name = form.cleaned_data["last_name"]
        request.user.email = form.cleaned_data["email"] or None
        request.user.phone_number = form.cleaned_data["phone_number"] or None

        try:
            request.user.save(
                update_fields=[
                    "display_name",
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                ]
            )
        except IntegrityError:
            form.add_error(None, _("Profile could not be saved because email or phone number is already in use."))
            return self.render_to_response(self.get_context_data(form=form))

        self.get_identity_user_audit_service().record_updated(
            user=request.user,
            before_data=before_data,
            **build_audit_request_context(request),
        )
        messages.success(request, _("Profile updated successfully."))
        return redirect(reverse("identity:current_user_profile"))

    def _build_profile_initial_data(self):
        user = self.request.user
        return {
            "display_name": getattr(user, "display_name", "") or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "email": user.email or "",
            "phone_number": getattr(user, "phone_number", "") or "",
        }

    def _build_profile_summary(self):
        return self.get_profile_summary_service().build(self.request.user)


class CurrentUserChangePasswordView(AuthenticateTemplateView):
    template_name = "identity/admin/change_password.html"
    layout_nav_key = "ADMIN_CHANGE_PASSWORD"
    password_form_class = CurrentUserChangePasswordForm
    identity_user_audit_service_class = IdentityUserAuditService

    def get_password_form(self, *args, **kwargs):
        kwargs.setdefault("user", self.request.user)
        return self.password_form_class(*args, **kwargs)

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", self.get_password_form())
        context["active_admin_section"] = "change_password"
        context["admin_back_url"] = reverse("dashboard:main")
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_password_form(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        request.user.set_password(form.cleaned_data["new_password"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        self.get_identity_user_audit_service().record_user_change_password(
            user=request.user,
            **build_audit_request_context(request),
        )
        messages.success(request, _("Password changed successfully."))
        return redirect(reverse("identity:current_user_change_password"))

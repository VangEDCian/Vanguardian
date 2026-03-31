from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.identity.application import (
    IdentityLoginAuditService,
    IdentityUserDirectoryQueryService,
    IdentityUserFilterActiveQueryService,
    IdentityUserFilterInactiveQueryService,
    IdentityUserNotFoundError,
)
from apps.identity.presentation.web.forms import StyledAuthenticationForm
from apps.shared.views.generic import AuthenticateTemplateView


class IdentityLoginView(LoginView):
    template_name = "identity/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard:main")
    login_audit_service_class = IdentityLoginAuditService

    def get_login_audit_service(self):
        return self.login_audit_service_class()

    def form_valid(self, form):
        response = super().form_valid(form)
        authenticated_user = form.get_user()
        self.get_login_audit_service().record_login_succeeded(
            request=self.request,
            user=authenticated_user,
            identifier=self._get_login_identifier(),
        )
        return response

    def form_invalid(self, form):
        self.get_login_audit_service().record_login_failed(
            request=self.request,
            identifier=self._get_login_identifier(),
            form_errors=form.errors.get_json_data(),
        )
        return super().form_invalid(form)

    def _get_login_identifier(self):
        return (self.request.POST.get("username") or "").strip()


class IdentityLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("identity:login")

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class IdentityUsersView(LoginRequiredMixin, AuthenticateTemplateView):
    template_name = "identity/users.html"
    layout_nav_key = "USERS"
    layout_breadcrumb_label = _("USERS")
    user_directory_query_service_class = IdentityUserDirectoryQueryService
    registered_filter_query_service_classes = (
        IdentityUserFilterActiveQueryService,
        IdentityUserFilterInactiveQueryService,
    )

    def get_user_directory_query_service(self):
        return self.user_directory_query_service_class(
            registered_filter_query_service_classes=self.registered_filter_query_service_classes
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            self.get_user_directory_query_service().list_users(
                search_query=self.request.GET.get("q", ""),
                filter_key=self.request.GET.get("filter", ""),
                sort_key=self.request.GET.get("sort", "username"),
                sort_direction=self.request.GET.get("direction", "asc"),
            )
        )
        return context


class IdentityUserDetailView(LoginRequiredMixin, AuthenticateTemplateView):
    template_name = "identity/user_detail.html"
    layout_nav_key = "USERS"
    user_directory_query_service_class = IdentityUserDirectoryQueryService
    detail_view_model = None

    def get_user_directory_query_service(self):
        return self.user_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        try:
            self.detail_view_model = self.get_user_directory_query_service().get_user_detail(
                user_id=kwargs["user_id"]
            )
        except IdentityUserNotFoundError as exc:
            raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self.detail_view_model is None:
            return super().get_layout_breadcrumb_label()
        return self.detail_view_model["layout_breadcrumb_label"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.detail_view_model is not None:
            context["detail_user"] = self.detail_view_model["detail_user"]
        return context

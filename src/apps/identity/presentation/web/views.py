from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.identity.forms import StyledAuthenticationForm
from apps.identity.models import User
from apps.shared.views.generic import AuthenticateTemplateView


class IdentityLoginView(LoginView):
    template_name = "identity/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard:main")


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get("q", "").strip()
        users_queryset = User.objects.order_by("username")

        if search_query:
            users_queryset = users_queryset.filter(
                Q(username__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone_number__icontains=search_query)
            )

        users = [self._build_user_row(user) for user in users_queryset]
        context["users"] = users
        context["users_total"] = len(users)
        context["user_search_query"] = search_query
        return context

    def _build_user_row(self, user):
        full_name = user.get_full_name().strip()
        role_label, role_tone = self._get_role_metadata(user)

        return {
            "username": user.get_username(),
            "display_name": full_name or user.get_username(),
            "email": user.email or "",
            "phone_number": getattr(user, "phone_number", "") or "",
            "role": role_label,
            "role_tone": role_tone,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
        }

    def _get_role_metadata(self, user):
        if user.is_superuser:
            return _("Administrator"), "admin"
        if user.is_staff:
            return _("Staff"), "staff"
        return _("User"), "user"

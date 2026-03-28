from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.formats import date_format
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
    users_table_headers = (
        _("USERNAME"),
        _("DISPLAY NAME"),
        _("EMAIL"),
        _("PHONE NUMBER"),
        _("ROLE"),
        _("STATUS"),
        _("JOINED DATE"),
        _("LAST LOGIN"),
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get("q", "").strip()
        status_filter = self.request.GET.get("status", "").strip().lower()
        users_queryset = User.objects.order_by("username")

        if status_filter == "active":
            users_queryset = users_queryset.filter(is_active=True)
        elif status_filter == "inactive":
            users_queryset = users_queryset.filter(is_active=False)

        if search_query:
            users_queryset = users_queryset.filter(
                Q(username__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone_number__icontains=search_query)
            )

        user_rows = [self._build_table_row(user) for user in users_queryset]
        context["users_table_headers"] = self.users_table_headers
        context["users_table_rows"] = user_rows
        context["users_total"] = len(user_rows)
        context["users_empty_text"] = _("No users found matching your criteria.")
        context["user_search_query"] = search_query
        context["user_status_filter"] = status_filter
        return context

    def _build_table_row(self, user):
        full_name = user.get_full_name().strip()
        role_label, role_tone = self._get_role_metadata(user)

        return {
            "selection_value": user.pk,
            "cells": [
                {
                    "kind": "text",
                    "value": user.get_username(),
                    "column_class": "entity-table__primary",
                },
                {
                    "kind": "text",
                    "value": full_name or user.get_username(),
                },
                self._build_text_cell(user.email, kind="secondary"),
                self._build_text_cell(getattr(user, "phone_number", "") or "", kind="secondary"),
                {
                    "kind": "role",
                    "value": role_label,
                    "tone": role_tone,
                },
                {
                    "kind": "state",
                    "value": _("Active") if user.is_active else _("Inactive"),
                    "tone": "active" if user.is_active else "inactive",
                },
                self._build_text_cell(
                    date_format(user.date_joined, "d-M-Y") if user.date_joined else ""
                ),
                self._build_text_cell(
                    date_format(user.last_login, "d-M-Y H:i") if user.last_login else ""
                ),
            ]
        }

    def _build_text_cell(self, value, kind="text"):
        if value:
            return {
                "kind": kind,
                "value": value,
            }

        return {
            "kind": "muted",
            "value": "—",
        }

    def _get_role_metadata(self, user):
        if user.is_superuser:
            return _("Administrator"), "admin"
        if user.is_staff:
            return _("Staff"), "staff"
        return _("User"), "user"

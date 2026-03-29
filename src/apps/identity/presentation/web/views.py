from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
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
        {"key": "username", "label": _("USERNAME")},
        {"key": "display_name", "label": _("DISPLAY NAME")},
        {"key": "email", "label": _("EMAIL")},
        {"key": "phone_number", "label": _("PHONE NUMBER")},
        {"key": "role", "label": _("ROLE")},
        {"key": "status", "label": _("STATUS")},
        {"key": "joined_date", "label": _("JOINED DATE")},
        {"key": "last_login", "label": _("LAST LOGIN")},
    )
    users_sortable_columns = (
        "username",
        "display_name",
        "email",
        "phone_number",
        "status",
        "joined_date",
        "last_login",
    )
    users_sort_map = {
        "username": ("username",),
        "display_name": ("first_name", "last_name", "username"),
        "email": ("email", "username"),
        "phone_number": ("phone_number", "username"),
        "status": ("is_active", "username"),
        "joined_date": ("date_joined", "username"),
        "last_login": ("last_login", "username"),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get("q", "").strip()
        status_filter = self.request.GET.get("status", "").strip().lower()
        sort_key = self.request.GET.get("sort", "username").strip()
        sort_direction = self.request.GET.get("direction", "asc").strip().lower()
        if sort_direction not in {"asc", "desc"}:
            sort_direction = "asc"
        if sort_key not in self.users_sort_map:
            sort_key = "username"

        users_queryset = User.objects.order_by(*self._build_order_by(sort_key, sort_direction))

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
        context["users_table_sortable_columns"] = self.users_sortable_columns
        context["users_table_sort_key"] = sort_key
        context["users_table_sort_direction"] = sort_direction
        context["users_table_sort_params"] = self._build_sort_params(search_query, status_filter)
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
            "detail_href": reverse("identity:user_detail", kwargs={"user_id": user.pk}),
            "cells": [
                {
                    "kind": "text",
                    "value": user.get_username(),
                    "column_class": "entity-table__primary is-detailed",
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

    def _build_order_by(self, sort_key, sort_direction):
        prefix = "-" if sort_direction == "desc" else ""
        return tuple(f"{prefix}{field_name}" for field_name in self.users_sort_map[sort_key])

    def _build_sort_params(self, search_query, status_filter):
        params = []
        if search_query:
            params.append({"name": "q", "value": search_query})
        if status_filter:
            params.append({"name": "status", "value": status_filter})
        return params

    @staticmethod
    def _get_role_metadata(user):
        if user.is_superuser:
            return _("Administrator"), "admin"
        if user.is_staff:
            return _("Staff"), "staff"
        return _("User"), "user"


class IdentityUserDetailView(LoginRequiredMixin, AuthenticateTemplateView):
    template_name = "identity/user_detail.html"
    layout_nav_key = "USERS"

    def dispatch(self, request, *args, **kwargs):
        self.user_object = get_object_or_404(User, pk=kwargs["user_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        return self.user_object.get_username()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.user_object
        full_name = user.get_full_name().strip()
        role_label, __ = IdentityUsersView._get_role_metadata(user)
        context["detail_user"] = {
            "username": user.get_username(),
            "display_name": full_name or user.get_username(),
            "email": user.email or "—",
            "phone_number": getattr(user, "phone_number", "") or "—",
            "role": role_label,
            "status": _("Active") if user.is_active else _("Inactive"),
            "date_joined": date_format(user.date_joined, "d-M-Y") if user.date_joined else "—",
            "last_login": date_format(user.last_login, "d-M-Y H:i") if user.last_login else "—",
            "back_url": reverse("identity:users"),
        }
        return context

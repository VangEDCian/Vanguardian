from django.contrib.auth.models import Group
from django.db import DatabaseError
from django.db.models import Q
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.identity.models import Role, User
from apps.identity.application.queries.user_filters import IdentityUserFilterQueryService


class IdentityUserNotFoundError(Exception):
    pass


class IdentityUserDirectoryQueryService:
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

    def __init__(self, *, registered_filter_query_service_classes=()):
        self.registered_filter_query_services = [
            filter_query_service_class() for filter_query_service_class in registered_filter_query_service_classes
        ]

    def list_users(self, *, search_query="", filter_key="", sort_key="username", sort_direction="asc"):
        normalized_search_query = (search_query or "").strip()
        normalized_filter_key = (filter_key or "").strip().lower()
        normalized_sort_key = (sort_key or "username").strip()
        normalized_sort_direction = (sort_direction or "asc").strip().lower()
        if normalized_sort_direction not in {"asc", "desc"}:
            normalized_sort_direction = "asc"
        if normalized_sort_key not in self.users_sort_map:
            normalized_sort_key = "username"

        users_queryset = User.objects.order_by(*self._build_order_by(normalized_sort_key, normalized_sort_direction))

        active_filter_query_service = self._get_active_filter_query_service(normalized_filter_key)
        if active_filter_query_service is not None:
            users_queryset = active_filter_query_service.apply(users_queryset)

        if normalized_search_query:
            users_queryset = users_queryset.filter(
                Q(username__icontains=normalized_search_query)
                | Q(first_name__icontains=normalized_search_query)
                | Q(last_name__icontains=normalized_search_query)
                | Q(email__icontains=normalized_search_query)
                | Q(phone_number__icontains=normalized_search_query)
            )

        user_rows = [self._build_table_row(user) for user in users_queryset]

        return {
            "users_table_headers": self.users_table_headers,
            "users_table_rows": user_rows,
            "users_table_sortable_columns": self.users_sortable_columns,
            "users_table_sort_key": normalized_sort_key,
            "users_table_sort_direction": normalized_sort_direction,
            "users_table_sort_params": self._build_sort_params(
                normalized_search_query,
                normalized_filter_key,
            ),
            "users_total": len(user_rows),
            "users_empty_text": _("No users found matching your criteria."),
            "users_filters": self._build_filter_options(),
            "user_selected_filter": normalized_filter_key,
            "user_selected_filter_label": self._get_selected_filter_label(normalized_filter_key),
            "user_search_query": normalized_search_query,
        }

    def get_user_detail(self, *, user_id):
        user = User.objects.prefetch_related("groups").filter(pk=user_id).first()
        if user is None:
            raise IdentityUserNotFoundError(user_id)

        explicit_display_name = getattr(user, "display_name", "").strip()
        full_name = user.get_full_name().strip()
        display_name = explicit_display_name or full_name or user.get_username()
        role_label, role_tone = self._get_role_metadata(user)
        permission_groups = [group.name for group in user.groups.order_by("name")]

        return {
            "layout_breadcrumb_label": user.get_username(),
            "detail_user": {
                "username": user.get_username(),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": display_name,
                "email": user.email or "—",
                "email_value": user.email or "",
                "phone_number": getattr(user, "phone_number", "") or "—",
                "phone_number_value": getattr(user, "phone_number", "") or "",
                "role": role_label,
                "role_tone": role_tone,
                "role_options": self._build_role_options(role_label),
                "selected_role": role_label,
                "permission_groups": permission_groups,
                "permission_group_options": self._build_permission_group_options(permission_groups),
                "status": _("Active") if user.is_active else _("Inactive"),
                "status_tone": "active" if user.is_active else "inactive",
                "date_joined": date_format(user.date_joined, "d-M-Y") if user.date_joined else "—",
                "date_joined_value": date_format(user.date_joined, "d-M-Y") if user.date_joined else "",
                "last_login": date_format(user.last_login, "d-M-Y H:i") if user.last_login else "—",
                "last_login_value": date_format(user.last_login, "d-M-Y H:i") if user.last_login else "",
                "back_url": reverse("identity:users"),
            },
        }

    def _build_table_row(self, user):
        explicit_display_name = getattr(user, "display_name", "").strip()
        full_name = user.get_full_name().strip()
        display_name = explicit_display_name or full_name or user.get_username()
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
                    "value": display_name,
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
                self._build_text_cell(date_format(user.date_joined, "d-M-Y") if user.date_joined else ""),
                self._build_text_cell(date_format(user.last_login, "d-M-Y H:i") if user.last_login else ""),
            ],
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

    def _build_filter_options(self):
        options = [IdentityUserFilterQueryService().build_option()]
        options.extend(
            filter_query_service.build_option() for filter_query_service in self.registered_filter_query_services
        )
        return options

    def _get_active_filter_query_service(self, filter_key):
        for filter_query_service in self.registered_filter_query_services:
            if filter_query_service.key == filter_key:
                return filter_query_service
        return None

    def _get_selected_filter_label(self, filter_key):
        if not filter_key:
            return IdentityUserFilterQueryService.label

        active_filter_query_service = self._get_active_filter_query_service(filter_key)
        if active_filter_query_service is None:
            return IdentityUserFilterQueryService.label
        return active_filter_query_service.label

    @staticmethod
    def _build_sort_params(search_query, filter_key):
        params = []
        if search_query:
            params.append({"name": "q", "value": search_query})
        if filter_key:
            params.append({"name": "filter", "value": filter_key})
        return params

    @staticmethod
    def _get_role_metadata(user):
        if user.is_superuser:
            return _("Administrator"), "admin"
        if user.is_staff:
            return _("Staff"), "staff"
        return _("User"), "user"

    @staticmethod
    def _build_role_options(selected_role):
        try:
            role_names = list(Role.objects.order_by("name").values_list("name", flat=True))
        except DatabaseError:
            role_names = []

        if selected_role and selected_role not in role_names:
            role_names.insert(0, selected_role)
        if not role_names:
            role_names = [selected_role]

        return [
            {
                "value": role_name,
                "label": role_name,
                "selected": role_name == selected_role,
            }
            for role_name in role_names
            if role_name
        ]

    @staticmethod
    def _build_permission_group_options(selected_permission_groups):
        selected_group_names = list(selected_permission_groups)
        group_names = list(Group.objects.order_by("name").values_list("name", flat=True))

        for selected_group_name in selected_group_names:
            if selected_group_name not in group_names:
                group_names.append(selected_group_name)

        return [
            {
                "value": group_name,
                "label": group_name,
                "selected": group_name in selected_group_names,
            }
            for group_name in group_names
        ]

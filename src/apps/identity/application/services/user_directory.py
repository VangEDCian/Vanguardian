from django.db.models import Q
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.identity.application.services.user_filters import IdentityUserFilterQueryService
from apps.identity.infrastructure.repositories import DjangoIdentityUserRepository


class IdentityUserNotFoundError(Exception):
    pass


class IdentityUserDirectoryQueryService:
    repository_class = DjangoIdentityUserRepository
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

    def __init__(self, *, registered_filter_query_service_classes=(), repository=None):
        self.repository = repository or self.repository_class()
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

        users_queryset = self.repository.list_users(
            order_by=self._build_order_by(normalized_sort_key, normalized_sort_direction),
        )

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
        filter_options = self._build_filter_options()
        selected_filter_label = self._get_selected_filter_label(normalized_filter_key)

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
            "users_filters": filter_options,
            "user_selected_filter": normalized_filter_key,
            "user_selected_filter_label": selected_filter_label,
            "user_search_query": normalized_search_query,
            "users_table_toolbar": self._build_table_toolbar(
                total=len(user_rows),
                search_query=normalized_search_query,
                filter_key=normalized_filter_key,
                sort_key=normalized_sort_key,
                sort_direction=normalized_sort_direction,
                filters=filter_options,
                selected_filter_label=selected_filter_label,
            ),
        }

    def get_user_detail(self, *, user_id, include_deleted=False):
        user = self.repository.get_user_for_detail(user_id=user_id, include_deleted=include_deleted)
        if user is None:
            raise IdentityUserNotFoundError(user_id)

        user_is_deleted = bool(user.deleted)

        explicit_display_name = getattr(user, "display_name", "").strip()
        full_name = user.get_full_name().strip()
        display_name = explicit_display_name or full_name or user.get_username()
        role_key, role_label, role_tone = self._get_role_metadata(user)
        permission_group_records = list(user.groups.order_by("name"))
        permission_groups = [group.name for group in permission_group_records]

        return {
            "layout_breadcrumb_label": user.get_username(),
            "layout_detail_meta_items": (
                {
                    "label": _("Username"),
                    "value": user.get_username(),
                },
                {
                    "label": _("Display name"),
                    "value": display_name,
                },
            ),
            "detail_user": {
                "id": user.pk,
                "username": user.get_username(),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": display_name,
                "email": user.email or "—",
                "email_value": user.email or "",
                "phone_number": getattr(user, "phone_number", "") or "—",
                "phone_number_value": getattr(user, "phone_number", "") or "",
                "role_key": role_key,
                "role": role_label,
                "role_tone": role_tone,
                "role_options": self._build_role_options(role_key),
                "selected_role": role_key,
                "permission_groups": permission_groups,
                "permission_group_options": self._build_permission_group_options(permission_group_records),
                "is_active": user.is_active,
                "status": _("Active") if user.is_active else _("Inactive"),
                "status_tone": "active" if user.is_active else "inactive",
                "date_joined": date_format(user.date_joined, "DATE_FORMAT") if user.date_joined else "—",
                "date_joined_value": date_format(user.date_joined, "DATE_FORMAT") if user.date_joined else "",
                "last_login": date_format(user.last_login, "DATETIME_FORMAT") if user.last_login else "—",
                "last_login_value": date_format(user.last_login, "DATETIME_FORMAT") if user.last_login else "",
                "back_url": reverse("identity:users"),
                "update_url": reverse("identity:user_detail", kwargs={"user_id": user.pk}),
                "restore_url": reverse("identity:user_restore", kwargs={"user_id": user.pk}),
                "is_deleted": user_is_deleted,
            },
        }

    def _build_table_row(self, user):
        explicit_display_name = getattr(user, "display_name", "").strip()
        full_name = user.get_full_name().strip()
        display_name = explicit_display_name or full_name or user.get_username()
        __, role_label, role_tone = self._get_role_metadata(user)

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
                self._build_text_cell(date_format(user.date_joined, "DATE_FORMAT") if user.date_joined else ""),
                self._build_text_cell(date_format(user.last_login, "DATETIME_FORMAT") if user.last_login else ""),
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

    def _build_table_toolbar(
        self,
        *,
        total,
        search_query,
        filter_key,
        sort_key,
        sort_direction,
        filters,
        selected_filter_label,
    ):
        return {
            "filter": {
                "id": "user-filter",
                "name": "filter",
                "label": _("Filter:"),
                "aria_label": _("Filter users"),
                "display_text": selected_filter_label,
                "options": filters,
                "select_wrapper_class": "common-select--filter",
                "hidden_fields": self._build_hidden_fields(
                    q=search_query,
                    sort=sort_key,
                    direction=sort_direction,
                ),
            },
            "secondary_search": None,
            "summary": {
                "label": _("Total Users"),
                "value": total,
            },
            "search": {
                "name": "q",
                "value": search_query,
                "placeholder": _("Search users..."),
                "aria_label": _("Search users"),
                "show_icon": True,
                "hidden_fields": self._build_hidden_fields(
                    filter=filter_key,
                    sort=sort_key,
                    direction=sort_direction,
                ),
            },
        }

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
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

    @staticmethod
    def _get_role_metadata(user):
        if user.is_superuser:
            return "administrator", _("Administrator"), "admin"
        if user.is_staff:
            return "staff", _("Staff"), "staff"
        return "user", _("User"), "user"

    @staticmethod
    def _build_role_options(selected_role_key):
        return [
            {
                "value": role_key,
                "label": role_label,
                "selected": role_key == selected_role_key,
            }
            for role_key, role_label in (
                ("administrator", _("Administrator")),
                ("staff", _("Staff")),
                ("user", _("User")),
            )
        ]

    def _build_permission_group_options(self, selected_permission_groups):
        selected_group_ids = {str(group.pk) for group in selected_permission_groups}
        group_records = list(self.repository.list_groups())

        return [
            {
                "value": str(group.pk),
                "label": group.name,
                "selected": str(group.pk) in selected_group_ids,
            }
            for group in group_records
        ]

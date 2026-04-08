# from django.db.models import Q
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.study.application.queries.study_filters import StudyFilterQueryService
from apps.study.infrastructure.persistence.models import Study


class StudyNotFoundError(Exception):
    pass


class StudyDirectoryQueryService:
    studies_table_headers = (
        {"key": "code", "label": _("CODE")},
        {"key": "name", "label": _("NAME")},
        {"key": "sponsor", "label": _("SPONSOR")},
        {"key": "start_date", "label": _("START DATE")},
        {"key": "end_date", "label": _("END DATE")},
        {"key": "status", "label": _("STATUS")},
    )
    studies_sortable_columns = (
        "code",
        "name",
        "sponsor",
        "start_date",
        "end_date",
        "status",
    )
    studies_sort_map = {
        "code": ("code",),
        "name": ("name", "code"),
        "sponsor": ("sponsor", "code"),
        "start_date": ("start_date", "code"),
        "end_date": ("end_date", "code"),
        "status": ("is_active", "code"),
    }

    def __init__(self, *, registered_filter_query_service_classes=()):
        self.registered_filter_query_services = [
            filter_query_service_class() for filter_query_service_class in registered_filter_query_service_classes
        ]

    def list_studies(
        self,
        *,
        user=None,
        search_query="",
        code_filter="",
        filter_key="",
        sort_key="code",
        sort_direction="asc",
        can_search=True,
        can_filter_code=True,
        can_filter_status=True,
    ):
        normalized_search_query = (search_query or "").strip()
        normalized_code_filter = (code_filter or "").strip()
        normalized_filter_key = (filter_key or "").strip().lower()
        normalized_sort_key = (sort_key or "code").strip()
        normalized_sort_direction = (sort_direction or "asc").strip().lower()
        if normalized_sort_direction not in {"asc", "desc"}:
            normalized_sort_direction = "asc"
        if normalized_sort_key not in self.studies_sort_map:
            normalized_sort_key = "code"

        studies_queryset = Study.objects.filter(deleted=False).order_by(
            *self._build_order_by(normalized_sort_key, normalized_sort_direction)
        )

        # Data scope: only Django superusers bypass membership filtering.
        if user is not None and not user.is_superuser:
            from apps.identity.infrastructure.persistence.models import StudyMembership

            member_study_ids = StudyMembership.objects.filter(user=user, deleted=False).values_list(
                "study_id", flat=True
            )
            studies_queryset = studies_queryset.filter(pk__in=member_study_ids)

        active_filter_query_service = self._get_active_filter_query_service(normalized_filter_key)
        if active_filter_query_service is not None:
            studies_queryset = active_filter_query_service.apply(studies_queryset)

        if normalized_code_filter:
            studies_queryset = studies_queryset.filter(code__icontains=normalized_code_filter)

        if normalized_search_query:
            studies_queryset = studies_queryset.filter(name__icontains=normalized_search_query)

        study_rows = [self._build_table_row(study) for study in studies_queryset]
        filter_options = self._build_filter_options()
        selected_filter_label = self._get_selected_filter_label(normalized_filter_key)

        return {
            "studies_table_headers": self.studies_table_headers,
            "studies_table_rows": study_rows,
            "studies_table_sortable_columns": self.studies_sortable_columns,
            "studies_table_sort_key": normalized_sort_key,
            "studies_table_sort_direction": normalized_sort_direction,
            "studies_table_sort_params": self._build_sort_params(
                normalized_search_query,
                normalized_code_filter,
                normalized_filter_key,
            ),
            "studies_total": len(study_rows),
            "studies_empty_text": _("No studies found matching your criteria."),
            "studies_filters": filter_options,
            "study_selected_filter": normalized_filter_key,
            "study_selected_filter_label": selected_filter_label,
            "study_search_query": normalized_search_query,
            "study_code_filter": normalized_code_filter,
            "studies_table_toolbar": self._build_table_toolbar(
                total=len(study_rows),
                search_query=normalized_search_query,
                code_filter=normalized_code_filter,
                filter_key=normalized_filter_key,
                sort_key=normalized_sort_key,
                sort_direction=normalized_sort_direction,
                filters=filter_options,
                selected_filter_label=selected_filter_label,
                can_search=can_search,
                can_filter_code=can_filter_code,
                can_filter_status=can_filter_status,
            ),
        }

    def get_study_detail(self, *, study_id):
        study = Study.objects.filter(pk=study_id, deleted=False).first()
        if study is None:
            raise StudyNotFoundError(study_id)

        return {
            "layout_breadcrumb_label": study.code,
            "layout_detail_meta_items": (
                {
                    "label": _("Study Code"),
                    "value": study.code,
                },
                {
                    "value": _("Active") if study.is_active else _("Inactive"),
                },
            ),
            "detail_study": {
                "id": study.pk,
                "code": study.code,
                "name": study.name,
                "sponsor": study.sponsor,
                "start_date": date_format(study.start_date, "DATE_FORMAT") if study.start_date else "—",
                "end_date": date_format(study.end_date, "DATE_FORMAT") if study.end_date else "—",
                "description": study.description,
                "status": _("Active") if study.is_active else _("Inactive"),
                "is_active": study.is_active,
                "back_url": reverse("study:study_list"),
                "edit_url": reverse("study:study_update", kwargs={"study_id": study.pk}),
            },
        }

    def _build_table_row(self, study):
        return {
            "selection_value": study.pk,
            "detail_href": reverse("study:study_detail", kwargs={"study_id": study.pk}),
            "cells": [
                {
                    "kind": "text",
                    "value": study.code,
                    "column_class": "entity-table__primary is-detailed",
                },
                {"kind": "text", "value": study.name},
                {"kind": "text", "value": study.sponsor},
                self._build_text_cell(date_format(study.start_date, "DATE_FORMAT") if study.start_date else ""),
                self._build_text_cell(date_format(study.end_date, "DATE_FORMAT") if study.end_date else ""),
                {
                    "kind": "state",
                    "value": _("Active") if study.is_active else _("Inactive"),
                    "tone": "active" if study.is_active else "inactive",
                },
            ],
        }

    def _build_text_cell(self, value):
        if value:
            return {"kind": "text", "value": value}
        return {"kind": "muted", "value": "—"}

    def _build_order_by(self, sort_key, sort_direction):
        prefix = "-" if sort_direction == "desc" else ""
        return tuple(f"{prefix}{field_name}" for field_name in self.studies_sort_map[sort_key])

    def _build_table_toolbar(
        self,
        *,
        total,
        search_query,
        code_filter,
        filter_key,
        sort_key,
        sort_direction,
        filters,
        selected_filter_label,
        can_search,
        can_filter_code,
        can_filter_status,
    ):
        return {
            "filter": (
                {
                    "id": "study-filter",
                    "name": "filter",
                    "label": _("Filter:"),
                    "aria_label": _("Filter studies"),
                    "display_text": selected_filter_label,
                    "options": filters,
                    "select_wrapper_class": "common-select--filter",
                    "hidden_fields": self._build_hidden_fields(
                        q=search_query if can_search else "",
                        code=code_filter if can_filter_code else "",
                        sort=sort_key,
                        direction=sort_direction,
                    ),
                }
                if can_filter_status
                else None
            ),
            "secondary_search": (
                {
                    "name": "code",
                    "value": code_filter,
                    "placeholder": _("Filter by code..."),
                    "aria_label": _("Filter studies by code"),
                    "class_name": "entity-table__search--inline",
                    "hidden_fields": self._build_hidden_fields(
                        filter=filter_key if can_filter_status else "",
                        q=search_query if can_search else "",
                        sort=sort_key,
                        direction=sort_direction,
                    ),
                }
                if can_filter_code
                else None
            ),
            "summary": {
                "label": _("Total"),
                "value": total,
            },
            "search": (
                {
                    "name": "q",
                    "value": search_query,
                    "placeholder": _("Search by name..."),
                    "aria_label": _("Search studies by name"),
                    "show_icon": True,
                    "hidden_fields": self._build_hidden_fields(
                        filter=filter_key if can_filter_status else "",
                        sort=sort_key,
                        direction=sort_direction,
                        code=code_filter if can_filter_code else "",
                    ),
                }
                if can_search
                else None
            ),
        }

    def _build_filter_options(self):
        options = [StudyFilterQueryService().build_option()]
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
            return StudyFilterQueryService.label

        active_filter_query_service = self._get_active_filter_query_service(filter_key)
        if active_filter_query_service is None:
            return StudyFilterQueryService.label
        return active_filter_query_service.label

    @staticmethod
    def _build_sort_params(search_query, code_filter, filter_key):
        params = []
        if search_query:
            params.append({"name": "q", "value": search_query})
        if code_filter:
            params.append({"name": "code", "value": code_filter})
        if filter_key:
            params.append({"name": "filter", "value": filter_key})
        return params

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

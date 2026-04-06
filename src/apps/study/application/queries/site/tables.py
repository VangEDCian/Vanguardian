from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.identity.infrastructure.persistence.models import StudyMembership
from apps.study.application.queries.site.exceptions import SiteNotFoundError
from apps.study.models import Site


# ---------------------------------------------------------------------------
# Filter services  (mirror StudyFilterQueryService pattern)
# ---------------------------------------------------------------------------

class SiteFilterQueryService:
    key = ""
    label = _("All")

    def apply(self, queryset):
        return queryset

    def build_option(self):
        return {"value": self.key, "label": self.label}


class SiteFilterActiveQueryService(SiteFilterQueryService):
    key = "active"
    label = _("Active")

    def apply(self, queryset):
        return queryset.filter(is_active=True)


class SiteFilterInactiveQueryService(SiteFilterQueryService):
    key = "inactive"
    label = _("Inactive")

    def apply(self, queryset):
        return queryset.filter(is_active=False)


# ---------------------------------------------------------------------------
# Directory query service
# ---------------------------------------------------------------------------

class SiteDirectoryQueryService:
    sites_table_headers = (
        {"key": "code",         "label": _("CODE")},
        {"key": "name",         "label": _("NAME")},
        {"key": "investigator", "label": _("INVESTIGATOR")},
        {"key": "study",        "label": _("STUDY")},
        {"key": "status",       "label": _("STATUS")},
    )
    sites_sortable_columns = ("code", "name", "investigator", "study", "status")
    sites_sort_map = {
        "code":         ("code",),
        "name":         ("name", "code"),
        "investigator": ("investigator", "code"),
        "study":        ("study__code", "code"),
        "status":       ("is_active", "code"),
    }

    _registered_filter_classes = (
        SiteFilterActiveQueryService,
        SiteFilterInactiveQueryService,
    )

    def __init__(self):
        self._filters = [cls() for cls in self._registered_filter_classes]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_sites(self, *, request, user, can_search, can_filter_code, can_filter_study):
        search_query   = (request.GET.get("q",      "") if can_search      else "").strip()
        code_filter    = (request.GET.get("code",   "") if can_filter_code  else "").strip()
        study_filter   = (request.GET.get("study",  "") if can_filter_study else "").strip()
        filter_key     = (request.GET.get("filter", "")).strip().lower()
        sort_key       = (request.GET.get("sort",   "code")).strip()
        sort_direction = (request.GET.get("direction", "asc")).strip().lower()

        if sort_direction not in {"asc", "desc"}:
            sort_direction = "asc"
        if sort_key not in self.sites_sort_map:
            sort_key = "code"

        queryset = Site.objects.filter(deleted=False).select_related("study")

        # Scope by membership
        if not user.is_superuser:
            member_study_ids = StudyMembership.objects.filter(
                user=user, deleted=False
            ).values_list("study_id", flat=True)
            queryset = queryset.filter(study_id__in=member_study_ids)

        # Status filter
        active_filter = self._get_active_filter(filter_key)
        if active_filter is not None:
            queryset = active_filter.apply(queryset)

        # Code filter
        if code_filter:
            queryset = queryset.filter(code__icontains=code_filter)

        # Study filter (by study code)
        if study_filter:
            queryset = queryset.filter(study__code__icontains=study_filter)

        # Search (name / investigator)
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(investigator__icontains=search_query)
            )

        queryset = queryset.order_by(
            *self._build_order_by(sort_key, sort_direction)
        )

        rows           = [self._build_row(site) for site in queryset]
        filter_options = self._build_filter_options()
        selected_label = self._get_selected_filter_label(filter_key)

        return {
            "sites_table_headers":           self.sites_table_headers,
            "sites_table_rows":              rows,
            "sites_table_sortable_columns":  self.sites_sortable_columns,
            "sites_table_sort_key":          sort_key,
            "sites_table_sort_direction":    sort_direction,
            "sites_table_sort_params":       self._build_sort_params(
                search_query, code_filter, study_filter, filter_key,
            ),
            "sites_total":      len(rows),
            "sites_empty_text": _("No sites found matching your criteria."),
            "sites_table_toolbar": self._build_toolbar(
                total=len(rows),
                search_query=search_query,
                code_filter=code_filter,
                study_filter=study_filter,
                filter_key=filter_key,
                sort_key=sort_key,
                sort_direction=sort_direction,
                filter_options=filter_options,
                selected_label=selected_label,
                can_search=can_search,
                can_filter_code=can_filter_code,
                can_filter_study=can_filter_study,
            ),
        }

    def get_site_detail(self, *, site_id, user):
        site = Site.objects.filter(pk=site_id, deleted=False).select_related("study").first()
        if site is None:
            raise SiteNotFoundError(site_id)

        if not user.is_superuser:
            has_access = StudyMembership.objects.filter(
                user=user, study_id=site.study_id, deleted=False,
            ).exists()
            if not has_access:
                raise SiteNotFoundError(site_id)

        return site

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_row(self, site):
        return {
            "selection_value": site.pk,
            "detail_href": reverse("study:site_detail", kwargs={"site_id": site.pk}),
            "cells": [
                {
                    "kind": "text",
                    "value": site.code,
                    "column_class": "entity-table__primary is-detailed",
                },
                {"kind": "text", "value": site.name},
                self._text_or_muted(site.investigator),
                {"kind": "text", "value": site.study.code if site.study else "—"},
                {
                    "kind": "state",
                    "value": _("Active") if site.is_active else _("Inactive"),
                    "tone": "active" if site.is_active else "inactive",
                },
            ],
        }

    def _text_or_muted(self, value):
        if value:
            return {"kind": "text", "value": value}
        return {"kind": "muted", "value": "—"}

    def _build_order_by(self, sort_key, sort_direction):
        prefix = "-" if sort_direction == "desc" else ""
        return tuple(f"{prefix}{f}" for f in self.sites_sort_map[sort_key])

    def _build_toolbar(
        self, *, total, search_query, code_filter, study_filter, filter_key,
        sort_key, sort_direction, filter_options, selected_label,
        can_search, can_filter_code, can_filter_study,
    ):
        return {
            "filter": (
                {
                    "id": "site-filter",
                    "name": "filter",
                    "label": _("Filter:"),
                    "aria_label": _("Filter sites"),
                    "display_text": selected_label,
                    "options": filter_options,
                    "select_wrapper_class": "common-select--filter",
                    "hidden_fields": self._hidden(
                        q=search_query if can_search else "",
                        code=code_filter if can_filter_code else "",
                        study=study_filter if can_filter_study else "",
                        sort=sort_key,
                        direction=sort_direction,
                    ),
                }
            ),
            "secondary_search": (
                {
                    "name": "code",
                    "value": code_filter,
                    "placeholder": _("Filter by code…"),
                    "aria_label": _("Filter sites by code"),
                    "class_name": "entity-table__search--inline",
                    "hidden_fields": self._hidden(
                        filter=filter_key,
                        q=search_query if can_search else "",
                        study=study_filter if can_filter_study else "",
                        sort=sort_key,
                        direction=sort_direction,
                    ),
                }
                if can_filter_code else None
            ),
            "study_search": (
                {
                    "name": "study",
                    "value": study_filter,
                    "placeholder": _("Filter by study…"),
                    "aria_label": _("Filter sites by study"),
                    "class_name": "entity-table__search--inline",
                    "hidden_fields": self._hidden(
                        filter=filter_key,
                        q=search_query if can_search else "",
                        code=code_filter if can_filter_code else "",
                        sort=sort_key,
                        direction=sort_direction,
                    ),
                }
                if can_filter_study else None
            ),
            "summary": {
                "label": _("Total"),
                "value": total,
            },
            "search": (
                {
                    "name": "q",
                    "value": search_query,
                    "placeholder": _("Search by name / investigator…"),
                    "aria_label": _("Search sites"),
                    "show_icon": True,
                    "hidden_fields": self._hidden(
                        filter=filter_key,
                        code=code_filter if can_filter_code else "",
                        study=study_filter if can_filter_study else "",
                        sort=sort_key,
                        direction=sort_direction,
                    ),
                }
                if can_search else None
            ),
        }

    def _build_filter_options(self):
        options = [SiteFilterQueryService().build_option()]
        options.extend(f.build_option() for f in self._filters)
        return options

    def _get_active_filter(self, filter_key):
        for f in self._filters:
            if f.key == filter_key:
                return f
        return None

    def _get_selected_filter_label(self, filter_key):
        if not filter_key:
            return SiteFilterQueryService.label
        active = self._get_active_filter(filter_key)
        return active.label if active else SiteFilterQueryService.label

    @staticmethod
    def _build_sort_params(search_query, code_filter, study_filter, filter_key):
        params = []
        if search_query:
            params.append({"name": "q",      "value": search_query})
        if code_filter:
            params.append({"name": "code",   "value": code_filter})
        if study_filter:
            params.append({"name": "study",  "value": study_filter})
        if filter_key:
            params.append({"name": "filter", "value": filter_key})
        return params

    @staticmethod
    def _hidden(**params):
        return [{"name": k, "value": v} for k, v in params.items() if v not in (None, "")]

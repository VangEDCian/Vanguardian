from django.db.models import Q
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.study.infrastructure.persistence.models import CrfTemplate


class StudyCrfTemplateDirectoryQueryService:
    crf_templates_table_headers = (
        {"key": "code", "label": _("CODE")},
        {"key": "name", "label": _("NAME")},
        {"key": "version", "label": _("VERSION")},
        {"key": "status", "label": _("STATUS")},
        {"key": "updated_at", "label": _("UPDATED AT")},
    )
    crf_templates_sortable_columns = ("code", "name", "version", "status", "updated_at")
    crf_templates_sort_map = {
        "code": ("code", "version"),
        "name": ("name", "code", "version"),
        "version": ("version", "code"),
        "status": ("is_active", "code", "version"),
        "updated_at": ("updated_at", "code", "version"),
    }

    def list_crf_templates(self, *, study_id, search_query="", sort_key="code", sort_direction="asc"):
        normalized_search_query = (search_query or "").strip()
        normalized_sort_key = (sort_key or "code").strip()
        normalized_sort_direction = (sort_direction or "asc").strip().lower()
        if normalized_sort_direction not in {"asc", "desc"}:
            normalized_sort_direction = "asc"
        if normalized_sort_key not in self.crf_templates_sort_map:
            normalized_sort_key = "code"

        crf_templates_queryset = CrfTemplate.objects.filter(
            study_id=study_id,
            deleted=False,
        ).order_by(*self._build_order_by(normalized_sort_key, normalized_sort_direction))

        if normalized_search_query:
            crf_templates_queryset = crf_templates_queryset.filter(
                Q(code__icontains=normalized_search_query)
                | Q(name__icontains=normalized_search_query)
                | Q(version__icontains=normalized_search_query)
            )

        crf_template_rows = [self._build_table_row(crf_template) for crf_template in crf_templates_queryset]

        return {
            "crf_templates_table_headers": self.crf_templates_table_headers,
            "crf_templates_table_rows": crf_template_rows,
            "crf_templates_table_sortable_columns": self.crf_templates_sortable_columns,
            "crf_templates_table_sort_key": normalized_sort_key,
            "crf_templates_table_sort_direction": normalized_sort_direction,
            "crf_templates_table_sort_params": self._build_sort_params(normalized_search_query),
            "crf_templates_total": len(crf_template_rows),
            "crf_templates_empty_text": _("No CRF templates found matching your criteria."),
            "crf_templates_table_toolbar": self._build_table_toolbar(
                total=len(crf_template_rows),
                search_query=normalized_search_query,
                sort_key=normalized_sort_key,
                sort_direction=normalized_sort_direction,
            ),
            "crf_template_search_query": normalized_search_query,
        }

    def _build_table_row(self, crf_template):
        return {
            "selection_value": crf_template.pk,
            "cells": [
                {
                    "kind": "text",
                    "value": crf_template.code,
                    "column_class": "entity-table__primary",
                },
                self._build_text_cell(crf_template.name),
                self._build_text_cell(crf_template.version),
                {
                    "kind": "state",
                    "value": _("Active") if crf_template.is_active else _("Inactive"),
                    "tone": "active" if crf_template.is_active else "inactive",
                },
                self._build_text_cell(date_format(crf_template.updated_at, "d-M-Y H:i") if crf_template.updated_at else ""),
            ],
        }

    def _build_text_cell(self, value):
        if value:
            return {"kind": "text", "value": value}
        return {"kind": "muted", "value": "—"}

    def _build_order_by(self, sort_key, sort_direction):
        prefix = "-" if sort_direction == "desc" else ""
        return tuple(f"{prefix}{field_name}" for field_name in self.crf_templates_sort_map[sort_key])

    def _build_table_toolbar(self, *, total, search_query, sort_key, sort_direction):
        return {
            "filter": None,
            "secondary_search": None,
            "summary": {
                "label": _("Total CRF Templates"),
                "value": total,
            },
            "search": {
                "name": "q",
                "value": search_query,
                "placeholder": _("Search CRF templates..."),
                "aria_label": _("Search CRF templates"),
                "show_icon": True,
                "hidden_fields": self._build_hidden_fields(sort=sort_key, direction=sort_direction),
            },
        }

    @staticmethod
    def _build_sort_params(search_query):
        params = []
        if search_query:
            params.append({"name": "q", "value": search_query})
        return params

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

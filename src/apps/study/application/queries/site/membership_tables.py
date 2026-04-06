from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.study.application.commands.site.membership_exceptions import SiteMembershipNotFoundError
from apps.study.models import SiteMembership


class SiteMembershipQueryService:
    table_headers = (
        {"key": "username",     "label": _("USERNAME")},
        {"key": "full_name",    "label": _("FULL NAME")},
        {"key": "study",        "label": _("STUDY")},
    )
    sortable_columns = ("username", "full_name", "study")
    sort_map = {
        "username":  ("user__username",),
        "full_name": ("user__last_name", "user__first_name"),
        "study":     ("study__code",),
    }

    def list_memberships(self, *, request, site_id):
        sort_key       = (request.GET.get("sort",      "username")).strip()
        sort_direction = (request.GET.get("direction", "asc")).strip().lower()

        if sort_direction not in {"asc", "desc"}:
            sort_direction = "asc"
        if sort_key not in self.sort_map:
            sort_key = "username"

        prefix   = "-" if sort_direction == "desc" else ""
        order_by = tuple(f"{prefix}{f}" for f in self.sort_map[sort_key])

        queryset = (
            SiteMembership.objects
            .filter(site_id=site_id, deleted=False)
            .select_related("user", "study")
            .order_by(*order_by)
        )

        rows = [self._build_row(m, site_id) for m in queryset]

        return {
            "membership_table_headers":          self.table_headers,
            "membership_table_rows":             rows,
            "membership_table_sortable_columns": self.sortable_columns,
            "membership_table_sort_key":         sort_key,
            "membership_table_sort_direction":   sort_direction,
            "membership_table_sort_params":      [],
            "memberships_total":   len(rows),
            "memberships_empty_text": _("No members found for this site."),
        }

    def get_membership_detail(self, *, membership_id, site_id):
        membership = (
            SiteMembership.objects
            .filter(pk=membership_id, site_id=site_id, deleted=False)
            .select_related("user", "study", "site")
            .first()
        )
        if membership is None:
            raise SiteMembershipNotFoundError(membership_id)
        return membership

    def _build_row(self, membership, site_id):
        detail_url = reverse(
            "study:membership_detail",
            kwargs={"site_id": site_id, "membership_id": membership.pk},
        )
        user = membership.user
        full_name = user.get_full_name().strip() if user else "—"
        return {
            "selection_value": membership.pk,
            "detail_href": detail_url,
            "cells": [
                {
                    "kind": "text",
                    "value": user.username if user else "—",
                    "column_class": "entity-table__primary is-detailed",
                },
                self._text_or_muted(full_name),
                {"kind": "text", "value": membership.study.code if membership.study else "—"},
            ],
        }

    @staticmethod
    def _text_or_muted(value):
        if value:
            return {"kind": "text", "value": value}
        return {"kind": "muted", "value": "—"}

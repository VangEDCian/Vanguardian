from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.study.models import EventDefinition


class StudyEventDefinitionDirectoryQueryService:
    event_definitions_table_headers = (
        {"key": "code", "label": _("CODE")},
        {"key": "name", "label": _("NAME")},
        {"key": "event_type", "label": _("EVENT TYPE")},
        {"key": "timing_mode", "label": _("TIMING")},
        {"key": "sequence_no", "label": _("SEQUENCE")},
        {"key": "required", "label": _("REQUIRED")},
        {"key": "enabled", "label": _("ENABLED")},
    )
    event_definitions_sortable_columns = (
        "code",
        "name",
        "event_type",
        "timing_mode",
        "sequence_no",
        "required",
        "enabled",
    )
    event_definitions_sort_map = {
        "code": ("code",),
        "name": ("name", "code"),
        "event_type": ("event_type", "sequence_no", "code"),
        "timing_mode": ("timing_mode", "sequence_no", "code"),
        "sequence_no": ("sequence_no", "code"),
        "required": ("is_required", "sequence_no", "code"),
        "enabled": ("is_enabled", "sequence_no", "code"),
    }

    def list_event_definitions(self, *, study_id, search_query="", sort_key="sequence_no", sort_direction="asc"):
        normalized_search_query = (search_query or "").strip()
        normalized_sort_key = (sort_key or "sequence_no").strip()
        normalized_sort_direction = (sort_direction or "asc").strip().lower()
        if normalized_sort_direction not in {"asc", "desc"}:
            normalized_sort_direction = "asc"
        if normalized_sort_key not in self.event_definitions_sort_map:
            normalized_sort_key = "sequence_no"

        event_definitions_queryset = EventDefinition.objects.filter(
            study_id=study_id,
            deleted=False,
        ).order_by(*self._build_order_by(normalized_sort_key, normalized_sort_direction))

        if normalized_search_query:
            event_definitions_queryset = event_definitions_queryset.filter(
                Q(code__icontains=normalized_search_query)
                | Q(name__icontains=normalized_search_query)
                | Q(description__icontains=normalized_search_query)
                | Q(event_type__icontains=normalized_search_query)
                | Q(timing_mode__icontains=normalized_search_query)
                | Q(anchor_event_code__icontains=normalized_search_query)
            )

        event_definitions = list(event_definitions_queryset)

        return {
            "event_definitions_table_headers": self.event_definitions_table_headers,
            "event_definitions_table_rows": [self._build_table_row(event_definition) for event_definition in event_definitions],
            "event_definitions_table_sortable_columns": self.event_definitions_sortable_columns,
            "event_definitions_table_sort_key": normalized_sort_key,
            "event_definitions_table_sort_direction": normalized_sort_direction,
            "event_definitions_table_sort_params": self._build_sort_params(normalized_search_query),
            "event_definitions_empty_text": _("No event definitions found matching your criteria."),
            "event_definitions_table_toolbar": self._build_table_toolbar(
                total=len(event_definitions),
                search_query=normalized_search_query,
                sort_key=normalized_sort_key,
                sort_direction=normalized_sort_direction,
            ),
            "event_definitions_diagram_nodes": self._build_diagram_nodes(event_definitions),
            "event_definitions_diagram_links": self._build_diagram_links(event_definitions),
        }

    def _build_table_row(self, event_definition):
        return {
            "selection_value": event_definition.pk,
            "cells": [
                {
                    "kind": "text",
                    "value": event_definition.code,
                    "column_class": "entity-table__primary",
                },
                self._build_text_cell(event_definition.name),
                self._build_text_cell(event_definition.event_type),
                self._build_text_cell(event_definition.timing_mode),
                self._build_text_cell(str(event_definition.sequence_no)),
                {
                    "kind": "state",
                    "value": _("Required") if event_definition.is_required else _("Optional"),
                    "tone": "active" if event_definition.is_required else "inactive",
                },
                {
                    "kind": "state",
                    "value": _("Enabled") if event_definition.is_enabled else _("Disabled"),
                    "tone": "active" if event_definition.is_enabled else "inactive",
                },
            ],
        }

    def _build_text_cell(self, value):
        if value not in (None, ""):
            return {"kind": "text", "value": value}
        return {"kind": "muted", "value": "—"}

    def _build_order_by(self, sort_key, sort_direction):
        prefix = "-" if sort_direction == "desc" else ""
        return tuple(f"{prefix}{field_name}" for field_name in self.event_definitions_sort_map[sort_key])

    def _build_table_toolbar(self, *, total, search_query, sort_key, sort_direction):
        return {
            "filter": None,
            "secondary_search": None,
            "summary": {
                "label": _("Total Event Definitions"),
                "value": total,
            },
            "search": {
                "name": "q",
                "value": search_query,
                "placeholder": _("Search event definitions..."),
                "aria_label": _("Search event definitions"),
                "show_icon": True,
                "hidden_fields": self._build_hidden_fields(
                    sort=sort_key,
                    direction=sort_direction,
                ),
            },
        }

    def _build_diagram_nodes(self, event_definitions):
        nodes = []
        for event_definition in sorted(event_definitions, key=lambda item: (item.sequence_no, item.code)):
            subtitle_parts = [event_definition.event_type, event_definition.timing_mode]
            if event_definition.day_offset is not None:
                subtitle_parts.append(f"Day {event_definition.day_offset}")
            if event_definition.is_repeating:
                subtitle_parts.append(_("Repeating"))

            nodes.append({
                "key": event_definition.code,
                "label": event_definition.name,
                "code": event_definition.code,
                "subtitle": " | ".join(str(part) for part in subtitle_parts if part),
                "sequence": event_definition.sequence_no,
                "fill": self._get_node_fill(event_definition),
                "stroke": "#1e88b9" if event_definition.is_enabled else "#9aa7b2",
            })
        return nodes

    def _build_diagram_links(self, event_definitions):
        event_definitions = sorted(event_definitions, key=lambda item: (item.sequence_no, item.code))
        event_by_code = {event_definition.code: event_definition for event_definition in event_definitions}
        links = []

        for index, event_definition in enumerate(event_definitions):
            if event_definition.anchor_event_code and event_definition.anchor_event_code in event_by_code:
                links.append({
                    "from": event_definition.anchor_event_code,
                    "to": event_definition.code,
                })
                continue

            if index == 0:
                continue

            previous = event_definitions[index - 1]
            links.append({
                "from": previous.code,
                "to": event_definition.code,
            })

        return links

    @staticmethod
    def _get_node_fill(event_definition):
        if not event_definition.is_enabled:
            return "#eef1f4"
        if event_definition.event_type == "common":
            return "#e8f4fb"
        return "#fdf2e2"

    @staticmethod
    def _build_sort_params(search_query):
        params = []
        if search_query:
            params.append({"name": "q", "value": search_query})
        return params

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.choices import EventDefinitionTypeChoices
from apps.study.models import EventDefinition, EventTransitionRule


class StudyEventDefinitionDirectoryQueryService:
    event_definitions_table_headers = (
        {"key": "code", "label": _("CODE")},
        {"key": "study_version", "label": _("VERSION")},
        {"key": "name", "label": _("NAME")},
        {"key": "event_type", "label": _("EVENT TYPE")},
        {"key": "timing_mode", "label": _("TIMING")},
        {"key": "sequence_no", "label": _("SEQUENCE")},
        {"key": "required", "label": _("REQUIRED")},
        {"key": "enabled", "label": _("ENABLED")},
    )
    event_definitions_sortable_columns = (
        "code",
        "study_version",
        "name",
        "event_type",
        "timing_mode",
        "sequence_no",
        "required",
        "enabled",
    )
    event_definitions_sort_map = {
        "code": ("study_version", "code"),
        "study_version": ("study_version", "sequence_no", "code"),
        "name": ("study_version", "name", "code"),
        "event_type": ("study_version", "event_type", "sequence_no", "code"),
        "timing_mode": ("study_version", "timing_mode", "sequence_no", "code"),
        "sequence_no": ("study_version", "sequence_no", "code"),
        "required": ("study_version", "is_required", "sequence_no", "code"),
        "enabled": ("study_version", "is_enabled", "sequence_no", "code"),
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
                Q(study_version__icontains=normalized_search_query)
                | Q(code__icontains=normalized_search_query)
                | Q(name__icontains=normalized_search_query)
                | Q(description__icontains=normalized_search_query)
                | Q(event_type__icontains=normalized_search_query)
                | Q(timing_mode__icontains=normalized_search_query)
                | Q(event_category__icontains=normalized_search_query)
                | Q(execution_mode__icontains=normalized_search_query)
            )

        event_definitions = list(event_definitions_queryset)
        transition_rules = list(
            EventTransitionRule.objects.select_related("from_event_definition", "to_event_definition")
            .filter(
                study_id=study_id,
                deleted=False,
                from_event_definition__deleted=False,
                to_event_definition__deleted=False,
            )
            .order_by("study_version", "display_order", "id")
        )

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
            "event_definitions_diagram_links": self._build_diagram_links(event_definitions, transition_rules),
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
                self._build_text_cell(event_definition.study_version),
                self._build_text_cell(event_definition.name),
                self._build_text_cell(event_definition.get_event_type_display()),
                self._build_text_cell(event_definition.get_timing_mode_display()),
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
        for event_definition in sorted(event_definitions, key=lambda item: (item.study_version, item.sequence_no, item.code)):
            subtitle_parts = [
                event_definition.study_version,
                event_definition.get_event_type_display(),
                event_definition.get_timing_mode_display(),
            ]
            if event_definition.event_category:
                subtitle_parts.append(event_definition.get_event_category_display())
            if event_definition.execution_mode:
                subtitle_parts.append(event_definition.get_execution_mode_display())
            if event_definition.is_repeating:
                subtitle_parts.append(_("Repeating"))

            nodes.append(
                {
                    "key": str(event_definition.pk),
                    "label": event_definition.name,
                    "title": f"{event_definition.study_version} · {event_definition.sequence_no}. {event_definition.code}",
                    "code": event_definition.code,
                    "subtitle": " | ".join(str(part) for part in subtitle_parts if part),
                    "sequence": event_definition.sequence_no,
                    "fill": self._get_node_fill(event_definition),
                    "stroke": "#1e88b9" if event_definition.is_enabled else "#9aa7b2",
                }
            )
        return nodes

    def _build_diagram_links(self, event_definitions, transition_rules):
        event_by_id = {event_definition.pk: event_definition for event_definition in event_definitions}
        links = []

        for transition_rule in transition_rules:
            from_event = event_by_id.get(transition_rule.from_event_definition_id)
            to_event = event_by_id.get(transition_rule.to_event_definition_id)
            if from_event is None or to_event is None:
                continue

            links.append(
                {
                    "from": str(transition_rule.from_event_definition_id),
                    "to": str(transition_rule.to_event_definition_id),
                    "label": self._build_transition_label(transition_rule),
                    "stroke": "#90a4b4" if transition_rule.is_enabled else "#c6ccd2",
                    "strokeDashArray": None if transition_rule.is_enabled else [6, 3],
                }
            )

        return links

    @staticmethod
    def _get_node_fill(event_definition):
        if not event_definition.is_enabled:
            return "#eef1f4"
        if event_definition.execution_mode == "workflow_action":
            return "#f2e8ff"
        if event_definition.event_category == "randomization":
            return "#e9f7ef"
        if event_definition.event_type == EventDefinitionTypeChoices.COMMON:
            return "#e8f4fb"
        return "#fdf2e2"

    def _build_transition_label(self, transition_rule):
        label_parts = [transition_rule.get_transition_type_display()]

        if transition_rule.condition_code:
            label_parts.append(self._humanize_code(transition_rule.condition_code))
        elif transition_rule.condition_scope and transition_rule.condition_scope != "subject_event":
            label_parts.append(transition_rule.get_condition_scope_display())

        if transition_rule.offset_days is not None:
            label_parts.append(_("Day %(day)s") % {"day": transition_rule.offset_days})

        if transition_rule.window_before_days is not None or transition_rule.window_after_days is not None:
            before_days = transition_rule.window_before_days or 0
            after_days = transition_rule.window_after_days or 0
            label_parts.append(
                _("Window -%(before)s/+%(after)s") % {
                    "before": before_days,
                    "after": after_days,
                }
            )

        return " | ".join(str(part) for part in label_parts if part)

    @staticmethod
    def _humanize_code(value):
        return " ".join(str(value).replace("_", " ").replace("-", " ").split()).title()

    @staticmethod
    def _build_sort_params(search_query):
        params = []
        if search_query:
            params.append({"name": "q", "value": search_query})
        return params

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

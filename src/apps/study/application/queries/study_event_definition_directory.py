from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.choices import EventDefinitionTypeChoices
from apps.study.models import EventDefinition, EventTransitionRule


class StudyEventDefinitionDirectoryQueryService:
    def list_event_definitions(self, *, study_id, search_query="", sort_query=""):
        normalized_search_query = (search_query or "").strip()

        event_definitions_queryset = EventDefinition.objects.filter(
            study_id=study_id,
            deleted=False,
        ).order_by("study_version", "sequence_no", "code", "pk")

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
        diagram_context = self.build_diagram_context(
            study_id=study_id,
            event_definitions=event_definitions,
        )

        return {
            "event_definitions": event_definitions,
            "event_definitions_total": len(event_definitions),
            "event_definitions_empty_text": _("No event definitions found matching your criteria."),
            "event_definitions_table_toolbar": self._build_table_toolbar(
                total=len(event_definitions),
                search_query=normalized_search_query,
                sort_query=sort_query,
            ),
            **diagram_context,
        }

    def build_diagram_context(self, *, study_id, event_definitions):
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
        diagram_nodes = self._build_diagram_nodes(event_definitions)
        diagram_links = self._build_diagram_links(event_definitions, transition_rules)
        return {
            "event_definitions_diagram_has_nodes": bool(diagram_nodes),
            "event_definitions_diagram_mermaid": self._build_diagram_mermaid(diagram_nodes, diagram_links),
        }

    def _build_table_toolbar(self, *, total, search_query, sort_query):
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
                "hidden_fields": self._build_hidden_fields(sort=sort_query),
            },
        }

    def _build_diagram_nodes(self, event_definitions):
        nodes = []
        for event_definition in sorted(event_definitions, key=lambda item: (item.study_version, item.sequence_no, item.code)):
            subtitle_parts = [
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
                    "title": f"{event_definition.sequence_no}. {event_definition.code}",
                    "code": event_definition.code,
                    "subtitle": " | ".join(str(part) for part in subtitle_parts if part),
                    "study_version": event_definition.study_version,
                    "sequence": event_definition.sequence_no,
                    "fill": self._get_node_fill(event_definition),
                    "stroke": "#1e88b9" if event_definition.is_enabled else "#9aa7b2",
                    "text": "#1b2b34" if event_definition.is_enabled else "#6a7885",
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

    def _build_diagram_mermaid(self, nodes, links):
        if not nodes:
            return ""

        mermaid_lines = ["flowchart LR"]

        for node in nodes:
            mermaid_lines.append(
                f'  {self._build_mermaid_node_id(node["key"])}["{self._build_mermaid_node_label(node)}"]'
            )

        for link in links:
            mermaid_lines.append(
                "  "
                f'{self._build_mermaid_node_id(link["from"])} -->|{self._build_mermaid_edge_label(link["label"])}| '
                f'{self._build_mermaid_node_id(link["to"])}'
            )

        for node in nodes:
            mermaid_lines.append(
                "  "
                f'style {self._build_mermaid_node_id(node["key"])} '
                f'fill:{node["fill"]},stroke:{node["stroke"]},stroke-width:1.5px,color:{node["text"]}'
            )

        for link_index, link in enumerate(links):
            mermaid_lines.append(
                f'  linkStyle {link_index} stroke:{link["stroke"]},stroke-width:1.5px'
            )

        return "\n".join(mermaid_lines)

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
            label_parts.append(
                _("Window -%(before)s/+%(after)s")
                % {
                    "before": transition_rule.window_before_days if transition_rule.window_before_days is not None else 0,
                    "after": transition_rule.window_after_days if transition_rule.window_after_days is not None else 0,
                }
            )

        return " | ".join(str(part) for part in label_parts if part)

    @staticmethod
    def _humanize_code(value):
        return " ".join(str(value).replace("_", " ").replace("-", " ").split()).title()

    @staticmethod
    def _build_mermaid_node_id(node_key):
        return f"event_{node_key}"

    @staticmethod
    def _build_mermaid_node_label(node):
        label_lines = [node["title"], node["label"]]
        if node["subtitle"]:
            label_lines.append(node["subtitle"].replace(" | ", " · "))
        return "<br/>".join(
            StudyEventDefinitionDirectoryQueryService._escape_mermaid_text(line)
            for line in label_lines
            if line
        )

    @staticmethod
    def _build_mermaid_edge_label(label):
        return StudyEventDefinitionDirectoryQueryService._escape_mermaid_text(
            str(label or "").replace(" | ", " · ")
        )

    @staticmethod
    def _escape_mermaid_text(value):
        return (
            str(value)
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

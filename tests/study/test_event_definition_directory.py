from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.study.application.queries.study_event_definition_directory import (
    StudyEventDefinitionDirectoryQueryService,
)


def _make_event_definition(
    *,
    pk,
    study_version,
    sequence_no,
    code,
    name,
    event_type="visit_based",
    timing_mode="scheduled",
    event_category=None,
    execution_mode="form_entry",
    is_enabled=True,
    is_required=False,
    is_repeating=False,
):
    return SimpleNamespace(
        pk=pk,
        study_version=study_version,
        sequence_no=sequence_no,
        code=code,
        name=name,
        event_type=event_type,
        timing_mode=timing_mode,
        event_category=event_category,
        execution_mode=execution_mode,
        is_enabled=is_enabled,
        is_required=is_required,
        is_repeating=is_repeating,
        get_event_type_display=lambda: event_type.replace("_", " ").title(),
        get_timing_mode_display=lambda: timing_mode.replace("_", " ").title(),
        get_event_category_display=lambda: (event_category or "").replace("_", " ").title(),
        get_execution_mode_display=lambda: execution_mode.replace("_", " ").title(),
    )


def _make_transition_rule(
    *,
    study_version,
    from_event_definition_id,
    to_event_definition_id,
    transition_type="conditional",
    condition_scope="subject_event",
    condition_code=None,
    offset_days=None,
    window_before_days=None,
    window_after_days=None,
    is_enabled=True,
):
    return SimpleNamespace(
        study_version=study_version,
        from_event_definition_id=from_event_definition_id,
        to_event_definition_id=to_event_definition_id,
        transition_type=transition_type,
        condition_scope=condition_scope,
        condition_code=condition_code,
        offset_days=offset_days,
        window_before_days=window_before_days,
        window_after_days=window_after_days,
        is_enabled=is_enabled,
        get_transition_type_display=lambda: transition_type.replace("_", " ").title(),
        get_condition_scope_display=lambda: condition_scope.replace("_", " ").title(),
    )


class StudyEventDefinitionDirectoryQueryServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = StudyEventDefinitionDirectoryQueryService()

    def test_builds_diagram_links_from_transition_rules(self):
        event_definitions = [
            _make_event_definition(
                pk=11,
                study_version="v1",
                sequence_no=1,
                code="SCREEN",
                name="Screening",
            ),
            _make_event_definition(
                pk=12,
                study_version="v1",
                sequence_no=2,
                code="RAND",
                name="Randomization",
                event_category="randomization",
            ),
        ]
        transition_rules = [
            _make_transition_rule(
                study_version="v1",
                from_event_definition_id=11,
                to_event_definition_id=12,
                condition_code="eligible",
                offset_days=3,
                window_before_days=1,
                window_after_days=2,
            )
        ]

        links = self.service._build_diagram_links(event_definitions, transition_rules)

        self.assertEqual(
            links,
            [
                {
                    "from": "11",
                    "to": "12",
                    "label": "Conditional | Eligible | Day 3 | Window -1/+2",
                    "stroke": "#90a4b4",
                    "strokeDashArray": None,
                }
            ],
        )

    def test_returns_no_links_when_version_has_no_transition_rules(self):
        event_definitions = [
            _make_event_definition(
                pk=21,
                study_version="v2",
                sequence_no=1,
                code="VISIT1",
                name="Visit 1",
            ),
            _make_event_definition(
                pk=22,
                study_version="v2",
                sequence_no=2,
                code="VISIT2",
                name="Visit 2",
            ),
            _make_event_definition(
                pk=23,
                study_version="v2",
                sequence_no=3,
                code="VISIT3",
                name="Visit 3",
            ),
        ]

        links = self.service._build_diagram_links(event_definitions, [])

        self.assertEqual(links, [])

    def test_returns_only_explicit_transition_rules(self):
        event_definitions = [
            _make_event_definition(
                pk=31,
                study_version="v3",
                sequence_no=1,
                code="SCREEN",
                name="Screening",
            ),
            _make_event_definition(
                pk=32,
                study_version="v3",
                sequence_no=2,
                code="RAND",
                name="Randomization",
                event_category="randomization",
            ),
            _make_event_definition(
                pk=33,
                study_version="v3",
                sequence_no=3,
                code="BASELINE",
                name="Baseline",
            ),
        ]
        transition_rules = [
            _make_transition_rule(
                study_version="v3",
                from_event_definition_id=31,
                to_event_definition_id=32,
                transition_type="automatic",
            )
        ]

        links = self.service._build_diagram_links(event_definitions, transition_rules)

        self.assertEqual(
            links,
            [
                {
                    "from": "31",
                    "to": "32",
                    "label": "Automatic",
                    "stroke": "#90a4b4",
                    "strokeDashArray": None,
                },
            ],
        )

    def test_builds_mermaid_flowchart_source(self):
        event_definitions = [
            _make_event_definition(
                pk=41,
                study_version="v1.0",
                sequence_no=1,
                code="SCREEN",
                name="Screening",
            ),
            _make_event_definition(
                pk=42,
                study_version="v1.0",
                sequence_no=2,
                code="RAND",
                name="Randomization",
                event_category="randomization",
                execution_mode="workflow_action",
            ),
        ]
        transition_rules = [
            _make_transition_rule(
                study_version="v1.0",
                from_event_definition_id=41,
                to_event_definition_id=42,
                transition_type="automatic",
                condition_code="eligible",
            )
        ]

        mermaid = self.service._build_diagram_mermaid(
            self.service._build_diagram_nodes(event_definitions),
            self.service._build_diagram_links(event_definitions, transition_rules),
        )

        self.assertIn("flowchart LR", mermaid)
        self.assertNotIn("Version v1.0", mermaid)
        self.assertIn('event_41["1. SCREEN<br/>Screening<br/>Visit Based · Scheduled · Form Entry"]', mermaid)
        self.assertIn('event_42["2. RAND<br/>Randomization<br/>Visit Based · Scheduled · Randomization · Workflow Action"]', mermaid)
        self.assertIn("event_41 -->|Automatic · Eligible| event_42", mermaid)
        self.assertIn("style event_41 fill:#fdf2e2,stroke:#1e88b9,stroke-width:1.5px,color:#1b2b34", mermaid)
        self.assertIn("style event_42 fill:#f2e8ff,stroke:#1e88b9,stroke-width:1.5px,color:#1b2b34", mermaid)
        self.assertIn("linkStyle 0 stroke:#90a4b4,stroke-width:1.5px", mermaid)

    def test_returns_empty_mermaid_source_without_nodes(self):
        self.assertEqual(self.service._build_diagram_mermaid([], []), "")

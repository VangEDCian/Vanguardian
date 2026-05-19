from django.test import SimpleTestCase

from apps.subject.domain import (
    StudyEventTransitionRuleSnapshot,
    SubjectEventInstanceSnapshot,
    SubjectEventTransitionPolicy,
)


class SubjectEventTransitionPolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = SubjectEventTransitionPolicy()
        self.source_event = SubjectEventInstanceSnapshot(
            id=10,
            study_id=1,
            subject_id=20,
            event_definition_id=100,
            study_version="1.0",
            repeat_index=1,
            status="verified",
        )
        self.target_event = SubjectEventInstanceSnapshot(
            id=11,
            study_id=1,
            subject_id=20,
            event_definition_id=101,
            study_version="1.0",
            repeat_index=1,
            status="not_ready",
        )

    def test_decide_allows_auto_open_when_source_verified_and_condition_is_true(self):
        rule = self._build_rule(transition_type="conditional", condition_code="baseline_ok")

        decisions = self.policy.decide(
            source_event=self.source_event,
            transition_rules=[rule],
            target_events_by_definition={101: self.target_event},
            facts={"baseline_ok": True},
        )

        self.assertEqual(len(decisions), 1)
        self.assertTrue(decisions[0].should_open)
        self.assertFalse(decisions[0].should_create)
        self.assertEqual(decisions[0].reason, "allowed")

    def test_decide_rejects_when_source_event_is_not_transition_ready(self):
        source_event = SubjectEventInstanceSnapshot(
            id=10,
            study_id=1,
            subject_id=20,
            event_definition_id=100,
            study_version="1.0",
            repeat_index=1,
            status="in_progress",
        )

        decisions = self.policy.decide(
            source_event=source_event,
            transition_rules=[self._build_rule()],
            target_events_by_definition={101: self.target_event},
            facts={},
        )

        self.assertFalse(decisions[0].should_open)
        self.assertEqual(decisions[0].reason, "source_event_not_transition_ready")

    def test_decide_allows_sequential_when_source_event_is_completed(self):
        source_event = SubjectEventInstanceSnapshot(
            id=10,
            study_id=1,
            subject_id=20,
            event_definition_id=100,
            study_version="1.0",
            repeat_index=1,
            status="completed",
        )

        decisions = self.policy.decide(
            source_event=source_event,
            transition_rules=[self._build_rule()],
            target_events_by_definition={101: self.target_event},
            facts={},
        )

        self.assertTrue(decisions[0].should_open)
        self.assertEqual(decisions[0].reason, "allowed")

    def test_decide_supports_auto_create_when_target_event_is_missing(self):
        rule = self._build_rule(auto_create=True)

        decisions = self.policy.decide(
            source_event=self.source_event,
            transition_rules=[rule],
            target_events_by_definition={},
            facts={},
        )

        self.assertFalse(decisions[0].should_open)
        self.assertTrue(decisions[0].should_create)
        self.assertEqual(decisions[0].reason, "allowed")

    def test_condition_code_from_condition_definition_code_is_evaluated_as_fact(self):
        rule = self._build_rule(
            transition_type="conditional",
            condition_code="baseline_ok",
            condition_definition_id=55,
        )

        decisions = self.policy.decide(
            source_event=self.source_event,
            transition_rules=[rule],
            target_events_by_definition={101: self.target_event},
            facts={"baseline_ok": True, "screen_failed": False},
        )

        self.assertTrue(decisions[0].should_open)

    def test_conditional_rule_evaluates_condition_definition_expression(self):
        rule = self._build_rule(
            transition_type="conditional",
            condition_code="eligible",
            condition_definition_id=55,
            condition_definition_scope="eligibility",
            condition_definition_code="eligible",
            condition_expression_json={
                "all": [
                    {"fact": "eligibility_form_verified", "op": "eq", "value": True},
                    {"fact": "required_eligibility_fields_verified", "op": "eq", "value": True},
                    {"fact": "no_blocking_eligibility_query", "op": "eq", "value": True},
                    {"fact": "pi_confirmed_eligibility", "op": "eq", "value": True},
                ],
            },
        )

        decisions = self.policy.decide(
            source_event=self.source_event,
            transition_rules=[rule],
            target_events_by_definition={101: self.target_event},
            facts={
                "eligibility_form_verified": True,
                "required_eligibility_fields_verified": True,
                "no_blocking_eligibility_query": True,
                "pi_confirmed_eligibility": True,
            },
        )

        self.assertTrue(decisions[0].should_open)

    def test_conditional_rule_rejects_when_condition_definition_expression_is_not_satisfied(self):
        rule = self._build_rule(
            transition_type="conditional",
            condition_code="eligible",
            condition_definition_id=55,
            condition_definition_scope="eligibility",
            condition_definition_code="eligible",
            condition_expression_json='{"all":[{"fact":"eligibility_form_verified","op":"eq","value":true}]}',
        )

        decisions = self.policy.decide(
            source_event=self.source_event,
            transition_rules=[rule],
            target_events_by_definition={101: self.target_event},
            facts={"eligibility_form_verified": False},
        )

        self.assertFalse(decisions[0].should_open)
        self.assertEqual(decisions[0].reason, "condition_not_satisfied")

    @staticmethod
    def _build_rule(
        *,
        condition_code=None,
        condition_definition_id=None,
        condition_definition_scope=None,
        condition_definition_code=None,
        condition_expression_json=None,
        transition_type="sequential",
        auto_open=True,
        auto_create=False,
    ):
        return StudyEventTransitionRuleSnapshot(
            id=1,
            from_event_definition_id=100,
            to_event_definition_id=101,
            transition_type=transition_type,
            condition_scope="subject_event",
            condition_code=condition_code,
            condition_definition_id=condition_definition_id,
            condition_definition_scope=condition_definition_scope,
            condition_definition_code=condition_definition_code,
            condition_expression_json=condition_expression_json,
            auto_open=auto_open,
            auto_create=auto_create,
            requires_previous_completion=True,
            allow_skip=False,
            display_order=1,
        )

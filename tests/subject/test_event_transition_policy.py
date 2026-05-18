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
        rule = self._build_rule(condition_code="baseline_ok")

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

    def test_decide_rejects_when_source_event_is_not_terminal(self):
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
        self.assertEqual(decisions[0].reason, "source_event_not_terminal")

    def test_decide_rejects_completed_event_because_completion_only_means_data_entry_done(self):
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

        self.assertFalse(decisions[0].should_open)
        self.assertEqual(decisions[0].reason, "source_event_not_terminal")

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

    def test_condition_expression_supports_and_or_not(self):
        rule = self._build_rule(
            condition_expression="baseline_ok and not screen_failed or override_open",
        )

        decisions = self.policy.decide(
            source_event=self.source_event,
            transition_rules=[rule],
            target_events_by_definition={101: self.target_event},
            facts={"baseline_ok": True, "screen_failed": False},
        )

        self.assertTrue(decisions[0].should_open)

    @staticmethod
    def _build_rule(
        *,
        condition_code=None,
        condition_expression=None,
        auto_open=True,
        auto_create=False,
    ):
        return StudyEventTransitionRuleSnapshot(
            id=1,
            from_event_definition_id=100,
            to_event_definition_id=101,
            transition_type="sequential",
            condition_scope="subject_event",
            condition_code=condition_code,
            condition_expression=condition_expression,
            auto_open=auto_open,
            auto_create=auto_create,
            requires_previous_completion=True,
            allow_skip=False,
            display_order=1,
        )

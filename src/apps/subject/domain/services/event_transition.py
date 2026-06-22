import json
from collections.abc import Mapping
from typing import Any

from apps.subject.domain.entities import (
    StudyEventTransitionRuleSnapshot,
    SubjectEventInstanceSnapshot,
    SubjectEventTransitionDecision,
)
from apps.subject.domain.status import SubjectEventInstance


class SubjectEventTransitionPolicy:
    TERMINAL_STATUSES = SubjectEventInstance.TERMINAL_STATUSES
    OPENABLE_STATUSES = SubjectEventInstance.OPENABLE_STATUSES
    TRANSITION_READY_STATUSES = SubjectEventInstance.TRANSITION_READY_STATUSES
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    INVALID_CONDITION_EXPRESSION = object()

    def decide(
        self,
        *,
        source_event: SubjectEventInstanceSnapshot,
        transition_rules: list[StudyEventTransitionRuleSnapshot],
        target_events_by_definition: Mapping[int, SubjectEventInstanceSnapshot],
        facts: Mapping[str, Any] | None = None,
    ) -> list[SubjectEventTransitionDecision]:
        normalized_facts = self._normalize_facts(facts or {})
        decisions: list[SubjectEventTransitionDecision] = []

        for rule in transition_rules:
            target_event = target_events_by_definition.get(rule.to_event_definition_id)
            is_allowed, reason = self._is_rule_allowed(
                source_event=source_event,
                target_event=target_event,
                rule=rule,
                facts=normalized_facts,
            )
            decisions.append(
                SubjectEventTransitionDecision(
                    rule_id=rule.id,
                    target_event_definition_id=rule.to_event_definition_id,
                    should_open=is_allowed and target_event is not None,
                    should_create=is_allowed and target_event is None and rule.auto_create,
                    reason=reason,
                )
            )

        return decisions

    def _is_rule_allowed(
        self,
        *,
        source_event: SubjectEventInstanceSnapshot,
        target_event: SubjectEventInstanceSnapshot | None,
        rule: StudyEventTransitionRuleSnapshot,
        facts: Mapping[str, Any],
    ) -> tuple[bool, str]:
        if not rule.auto_open:
            return False, "rule_auto_open_disabled"

        transition_type = self._normalized(rule.transition_type)
        source_event_is_transition_ready = SubjectEventInstance.is_transition_ready(source_event.status)

        if transition_type == self.SEQUENTIAL and not source_event_is_transition_ready:
            return False, "source_event_not_transition_ready"

        if rule.requires_previous_completion and not source_event_is_transition_ready:
            return False, "source_event_not_transition_ready"

        if target_event is not None and not SubjectEventInstance.is_openable(target_event.status):
            return False, "target_event_not_openable"

        if transition_type == self.SEQUENTIAL:
            condition_satisfied = True
        elif transition_type == self.CONDITIONAL:
            condition_satisfied = self._is_condition_satisfied(rule=rule, facts=facts)
        else:
            return False, "unsupported_transition_type"

        if not condition_satisfied:
            return False, "condition_not_satisfied"

        if target_event is None and not rule.auto_create:
            return False, "target_event_missing"

        return True, "allowed"

    def _is_condition_satisfied(
        self,
        *,
        rule: StudyEventTransitionRuleSnapshot,
        facts: Mapping[str, Any],
    ) -> bool:
        expression = self._parse_condition_expression(rule.condition_expression_json)
        if expression is self.INVALID_CONDITION_EXPRESSION:
            return False
        if expression is not None:
            if not self._has_condition_definition(rule):
                return False
            return self._evaluate_expression(expression, facts)

        condition_code = (rule.condition_code or "").strip()
        if not condition_code:
            return True

        return bool(facts.get(condition_code, False))

    @staticmethod
    def _normalize_facts(facts: Mapping[str, Any]) -> dict[str, Any]:
        return {str(key).strip(): value for key, value in facts.items() if str(key).strip()}

    @staticmethod
    def _normalized(value) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _has_condition_definition(rule: StudyEventTransitionRuleSnapshot) -> bool:
        return bool(
            rule.condition_definition_id
            and (rule.condition_definition_scope or rule.condition_scope or "").strip()
            and (rule.condition_definition_code or rule.condition_code or "").strip()
        )

    @staticmethod
    def _parse_condition_expression(expression_json):
        if expression_json in (None, ""):
            return None
        if isinstance(expression_json, Mapping):
            return expression_json
        try:
            parsed_expression = json.loads(expression_json)
        except (TypeError, json.JSONDecodeError):
            return SubjectEventTransitionPolicy.INVALID_CONDITION_EXPRESSION
        if not isinstance(parsed_expression, Mapping):
            return SubjectEventTransitionPolicy.INVALID_CONDITION_EXPRESSION
        return parsed_expression

    def _evaluate_expression(self, expression, facts: Mapping[str, Any]) -> bool:
        if "all" in expression:
            conditions = expression.get("all")
            return isinstance(conditions, list) and all(
                self._evaluate_expression(condition, facts) for condition in conditions
            )
        if "any" in expression:
            conditions = expression.get("any")
            return isinstance(conditions, list) and any(
                self._evaluate_expression(condition, facts) for condition in conditions
            )
        if "not" in expression:
            condition = expression.get("not")
            return isinstance(condition, Mapping) and not self._evaluate_expression(condition, facts)

        fact_key = str(expression.get("fact") or "").strip()
        if not fact_key:
            return False
        actual_value = facts.get(fact_key)
        expected_value = expression.get("value")
        operator = self._normalized(expression.get("op") or expression.get("operator") or "eq")
        return self._compare_fact_value(actual_value, operator, expected_value)

    def _compare_fact_value(self, actual_value, operator: str, expected_value) -> bool:
        operators = {
            "eq": lambda: actual_value == expected_value,
            "equals": lambda: actual_value == expected_value,
            "ne": lambda: actual_value != expected_value,
            "not_equals": lambda: actual_value != expected_value,
            "exists": lambda: actual_value is not None,
            "not_exists": lambda: actual_value is None,
            "in": lambda: self._is_in(actual_value, expected_value),
            "not_in": lambda: not self._is_in(actual_value, expected_value),
            "gt": lambda: self._compare_order(actual_value, expected_value, lambda left, right: left > right),
            "gte": lambda: self._compare_order(actual_value, expected_value, lambda left, right: left >= right),
            "lt": lambda: self._compare_order(actual_value, expected_value, lambda left, right: left < right),
            "lte": lambda: self._compare_order(actual_value, expected_value, lambda left, right: left <= right),
        }
        return operators.get(operator, lambda: False)()

    @staticmethod
    def _is_in(actual_value, expected_value) -> bool:
        return isinstance(expected_value, (list, tuple, set)) and actual_value in expected_value

    @staticmethod
    def _compare_order(actual_value, expected_value, comparator) -> bool:
        try:
            return comparator(actual_value, expected_value)
        except TypeError:
            return False


__all__ = ["SubjectEventTransitionPolicy"]

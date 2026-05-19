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
        facts: Mapping[str, bool],
    ) -> tuple[bool, str]:
        if not rule.auto_open:
            return False, "rule_auto_open_disabled"

        if rule.requires_previous_completion and not SubjectEventInstance.is_terminal(source_event.status):
            return False, "source_event_not_terminal"

        if target_event is not None and not SubjectEventInstance.is_openable(target_event.status):
            return False, "target_event_not_openable"

        if not self._is_condition_satisfied(rule=rule, facts=facts):
            return False, "condition_not_satisfied"

        if target_event is None and not rule.auto_create:
            return False, "target_event_missing"

        return True, "allowed"

    def _is_condition_satisfied(
        self,
        *,
        rule: StudyEventTransitionRuleSnapshot,
        facts: Mapping[str, bool],
    ) -> bool:
        condition_code = (rule.condition_code or "").strip()

        if not condition_code:
            return True

        return facts.get(condition_code, False)

    @staticmethod
    def _normalize_facts(facts: Mapping[str, Any]) -> dict[str, bool]:
        return {str(key).strip(): bool(value) for key, value in facts.items() if str(key).strip()}


__all__ = ["SubjectEventTransitionPolicy"]

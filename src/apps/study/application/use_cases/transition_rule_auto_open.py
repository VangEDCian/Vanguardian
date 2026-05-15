from collections import defaultdict
from typing import Mapping, Sequence

from apps.subject.domain import SubjectEventInstance


class StudyEventTransitionRuleAutoOpenUseCase:
    true_values = frozenset({"true", "1", "yes", "y"})
    false_values = frozenset({"false", "0", "no", "n"})

    def resolve_initial_status_by_event_definition(
        self,
        *,
        event_definitions: Sequence,
        transition_rules: Sequence,
        condition_flags: Mapping[str, bool] | None = None,
        existing_status_by_event_definition: Mapping[int, str] | None = None,
    ) -> dict[int, str]:
        flags = condition_flags or {}
        current_statuses = dict(existing_status_by_event_definition or {})
        incoming_rules_by_event_definition = defaultdict(list)

        for rule in transition_rules:
            incoming_rules_by_event_definition[rule.to_event_definition_id].append(rule)

        status_by_event_definition = {}
        for event_definition in event_definitions:
            incoming_rules = incoming_rules_by_event_definition.get(event_definition.pk, [])
            if not incoming_rules:
                resolved_status = SubjectEventInstance.OPEN
            else:
                can_auto_open = any(
                    self._can_auto_open(
                        transition_rule=transition_rule,
                        condition_flags=flags,
                        current_status_by_event_definition=current_statuses,
                    )
                    for transition_rule in incoming_rules
                )
                resolved_status = SubjectEventInstance.OPEN if can_auto_open else SubjectEventInstance.NOT_READY

            status_by_event_definition[event_definition.pk] = resolved_status
            current_statuses[event_definition.pk] = resolved_status

        return status_by_event_definition

    def _can_auto_open(
        self,
        *,
        transition_rule,
        condition_flags: Mapping[str, bool],
        current_status_by_event_definition: Mapping[int, str],
    ) -> bool:
        if transition_rule.requires_previous_completion:
            from_event_status = current_status_by_event_definition.get(
                transition_rule.from_event_definition_id,
                SubjectEventInstance.NOT_READY,
            )
            if not SubjectEventInstance.is_terminal(from_event_status):
                return False

        return self._is_rule_condition_satisfied(
            condition_code=transition_rule.condition_code,
            condition_expression=transition_rule.condition_expression,
            condition_flags=condition_flags,
        )

    def _is_rule_condition_satisfied(
        self,
        *,
        condition_code: str | None,
        condition_expression: str | None,
        condition_flags: Mapping[str, bool],
    ) -> bool:
        code_result = self._evaluate_condition_code(
            condition_code=condition_code,
            condition_flags=condition_flags,
        )
        expression_result = self._evaluate_condition_expression(
            condition_expression=condition_expression,
            condition_flags=condition_flags,
        )
        return code_result and expression_result

    def _evaluate_condition_code(
        self,
        *,
        condition_code: str | None,
        condition_flags: Mapping[str, bool],
    ) -> bool:
        code = (condition_code or "").strip()
        if not code:
            return True

        if code in condition_flags:
            return bool(condition_flags[code])

        code_lower = code.lower()
        if code_lower in condition_flags:
            return bool(condition_flags[code_lower])

        return False

    def _evaluate_condition_expression(  # noqa: C901
        self,
        *,
        condition_expression: str | None,
        condition_flags: Mapping[str, bool],
    ) -> bool:
        expression = (condition_expression or "").strip()
        if not expression:
            return True

        expression_lower = expression.lower()
        if expression_lower in self.true_values:
            return True
        if expression_lower in self.false_values:
            return False

        if " and " in expression_lower:
            return all(
                self._evaluate_condition_expression(
                    condition_expression=part,
                    condition_flags=condition_flags,
                )
                for part in expression.split(" and ")
            )

        if " or " in expression_lower:
            return any(
                self._evaluate_condition_expression(
                    condition_expression=part,
                    condition_flags=condition_flags,
                )
                for part in expression.split(" or ")
            )

        if expression_lower.startswith("not "):
            return not self._evaluate_condition_expression(
                condition_expression=expression[4:],
                condition_flags=condition_flags,
            )

        if "==" in expression:
            left_token, right_token = expression.split("==", 1)
            return self._resolve_token_value(left_token, condition_flags) == self._resolve_token_value(
                right_token,
                condition_flags,
            )

        if "!=" in expression:
            left_token, right_token = expression.split("!=", 1)
            return self._resolve_token_value(left_token, condition_flags) != self._resolve_token_value(
                right_token,
                condition_flags,
            )

        if expression in condition_flags:
            return bool(condition_flags[expression])

        if expression_lower in condition_flags:
            return bool(condition_flags[expression_lower])

        return False

    def _resolve_token_value(self, token: str, condition_flags: Mapping[str, bool]):
        normalized_token = token.strip()
        normalized_token_lower = normalized_token.lower()

        if normalized_token_lower in self.true_values:
            return True
        if normalized_token_lower in self.false_values:
            return False

        if (
            (normalized_token.startswith("'") and normalized_token.endswith("'"))
            or (normalized_token.startswith('"') and normalized_token.endswith('"'))
        ) and len(normalized_token) >= 2:
            return normalized_token[1:-1]

        if normalized_token in condition_flags:
            return condition_flags[normalized_token]
        if normalized_token_lower in condition_flags:
            return condition_flags[normalized_token_lower]

        return None

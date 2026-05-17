import ast
import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldValidationCheckResult:
    has_failures: bool
    failed_field_keys: tuple[str, ...]


def _to_eval_literal(raw_value):
    if raw_value is None:
        return ""
    if isinstance(raw_value, (dict, list, tuple)):
        return json.dumps(raw_value, ensure_ascii=False)
    return raw_value


def _normalize_expression(expression: str, value):
    normalized = str(expression or "").strip()
    normalized = normalized.replace("&&", " and ").replace("||", " or ")
    normalized = re.sub(r"!\s*(?!=)", " not ", normalized)
    normalized = re.sub(r"\btrue\b", "True", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bfalse\b", "False", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bnull\b", "None", normalized, flags=re.IGNORECASE)
    value_literal = repr(_to_eval_literal(value))
    return normalized.replace("$val", value_literal)


def _is_safe_expression_ast(expression: str) -> bool:
    try:
        root = ast.parse(expression, mode="eval")
    except SyntaxError:
        return False
    allowed_nodes = (
        ast.Expression,
        ast.BoolOp,
        ast.UnaryOp,
        ast.BinOp,
        ast.Compare,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.In,
        ast.NotIn,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
    )
    return all(isinstance(node, allowed_nodes) for node in ast.walk(root))


def check_field_err(*, expression: str, value) -> bool:
    normalized = _normalize_expression(expression, value)
    if not normalized:
        return False
    if not _is_safe_expression_ast(normalized):
        return True
    try:
        result = eval(normalized, {"__builtins__": {}}, {})  # noqa: S307
    except Exception:
        return True
    return not bool(result)


class DataCaptureFieldValidationRulesService:
    def __init__(self, repository):
        self.repository = repository

    def check_field_validation_rules(self, *, crf_template_id: int, payload_data: str) -> FieldValidationCheckResult:
        try:
            payload_map = json.loads(payload_data or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            payload_map = {}
        if not isinstance(payload_map, dict):
            payload_map = {}
        rules_by_field_key = self.repository.list_form_field_validation_rules(crf_template_id=crf_template_id)
        failed_field_keys: list[str] = []
        for field_key, expressions in rules_by_field_key.items():
            if not expressions:
                continue
            field_value = payload_map.get(field_key)
            has_error = any(check_field_err(expression=expression, value=field_value) for expression in expressions)
            if has_error:
                failed_field_keys.append(field_key)
        return FieldValidationCheckResult(
            has_failures=bool(failed_field_keys),
            failed_field_keys=tuple(sorted(set(failed_field_keys))),
        )


__all__ = [
    "DataCaptureFieldValidationRulesService",
    "FieldValidationCheckResult",
    "check_field_err",
]

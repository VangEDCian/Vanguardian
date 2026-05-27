from django.db import transaction
from django.utils import timezone

from apps.crf.domain.exceptions import FormBuilderDomainValidationError
from apps.crf.infrastructure.repositories import DjangoCrfValidationRuleImportRepository


class CrfValidationRuleImportAmbiguousError(FormBuilderDomainValidationError):
    """Raised when an import row resolves to more than one CRF object."""


class CrfValidationRuleImportNotFoundError(FormBuilderDomainValidationError):
    """Raised when an import row cannot resolve a referenced CRF object."""


class CrfValidationRuleImportService:
    repository_class = DjangoCrfValidationRuleImportRepository
    rule_type_values = {
        "REQUIRED",
        "CUSTOM_EXPRESSION",
    }
    mode_values = {"HARD", "SOFT", "QUERY"}
    rule_type_aliases = {
        "custom": "CUSTOM_EXPRESSION",
        "custom expression": "CUSTOM_EXPRESSION",
        "custom_expression": "CUSTOM_EXPRESSION",
    }
    mode_aliases = {
        "blocking": "HARD",
        "warning": "SOFT",
    }

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def resolve_template_by_code_or_id(self, *, study_id, form_code):
        templates = list(
            self.repository.find_template_by_code_or_id(
                study_id=study_id,
                form_code=form_code,
            )
        )
        if not templates:
            raise CrfValidationRuleImportNotFoundError(
                f"Form Code '{form_code}' was not found in this study."
            )
        if len(templates) > 1:
            raise CrfValidationRuleImportAmbiguousError(
                f"Form Code '{form_code}' is ambiguous in this study."
            )
        return templates[0]

    def resolve_template_by_code(self, *, study_id, form_code):
        templates = list(
            self.repository.find_template_by_code(
                study_id=study_id,
                form_code=form_code,
            )
        )
        if not templates:
            raise CrfValidationRuleImportNotFoundError(
                f"Form Code '{form_code}' was not found in this study."
            )
        if len(templates) > 1:
            raise CrfValidationRuleImportAmbiguousError(
                f"Form Code '{form_code}' is ambiguous in this study."
            )
        return templates[0]

    def resolve_field_by_name_or_id(self, *, crf_template_id, field_name):
        fields = list(
            self.repository.find_field_by_name_or_id(
                crf_template_id=crf_template_id,
                field_name=field_name,
            )
        )
        if not fields:
            raise CrfValidationRuleImportNotFoundError(
                f"Field Name '{field_name}' was not found in this form."
            )
        if len(fields) > 1:
            raise CrfValidationRuleImportAmbiguousError(
                f"Field Name '{field_name}' is ambiguous in this form."
            )
        return fields[0]

    def resolve_field_by_key(self, *, crf_template_id, field_name):
        fields = list(
            self.repository.find_field_by_key(
                crf_template_id=crf_template_id,
                field_name=field_name,
            )
        )
        if not fields:
            raise CrfValidationRuleImportNotFoundError(
                f"Field Name '{field_name}' was not found in this form."
            )
        if len(fields) > 1:
            raise CrfValidationRuleImportAmbiguousError(
                f"Field Name '{field_name}' is ambiguous in this form."
            )
        return fields[0]

    @transaction.atomic
    def upsert_validation_rule(
        self,
        *,
        study_id,
        crf_template_id,
        field_template_id,
        rule_type,
        expression,
        severity,
        mode,
        vi_message,
        en_message,
        actor_user_id,
        now=None,
    ):
        now = now or timezone.now()
        rule_type = self._normalize_rule_type(rule_type)
        mode = self._normalize_mode(mode)
        validation_rule = self.repository.find_validation_rule_for_import(
            field_template_id=field_template_id,
            rule_type=rule_type,
            expression=expression,
            mode=mode,
        )
        action = "updated"
        if validation_rule is None:
            action = "created"
            validation_rule = self.repository.build_validation_rule(
                field_template_id=field_template_id,
                created_at=now,
                created_by_id=actor_user_id,
            )

        validation_rule.study_id = study_id
        validation_rule.crf_template_id = crf_template_id
        validation_rule.rule_type = rule_type
        validation_rule.expression = expression
        validation_rule.severity = severity
        validation_rule.mode = mode
        validation_rule.deleted = False
        validation_rule.updated_at = now
        validation_rule.updated_by_id = actor_user_id
        self.repository.save_validation_rule(validation_rule)

        fallback_message = en_message or vi_message or expression
        for language_code, message in (
            ("en", en_message or fallback_message),
            ("vi", vi_message or fallback_message),
        ):
            validation_rule.set_current_language(language_code, initialize=True)
            validation_rule.message = message
            self.repository.save_validation_rule(validation_rule)

        return action, validation_rule

    @classmethod
    def _normalize_rule_type(cls, value):
        normalized = str(value or "").strip()
        normalized_key = normalized.replace("-", "_").strip().lower()
        rule_type = cls.rule_type_aliases.get(normalized_key, normalized_key.upper())
        if rule_type not in cls.rule_type_values:
            raise FormBuilderDomainValidationError(f"Rule Type '{value}' is not supported.")
        return rule_type

    @classmethod
    def _normalize_mode(cls, value):
        normalized = str(value or "").strip()
        normalized_key = normalized.replace("-", "_").strip().lower()
        mode = cls.mode_aliases.get(normalized_key, normalized_key.upper())
        if mode not in cls.mode_values:
            raise FormBuilderDomainValidationError(f"Mode '{value}' is not supported.")
        return mode


__all__ = [
    "CrfValidationRuleImportAmbiguousError",
    "CrfValidationRuleImportNotFoundError",
    "CrfValidationRuleImportService",
]

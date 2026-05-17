from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FieldDefinitionSection:
    sdtm: dict
    unit: str | None
    range_min: Decimal | None
    range_max: Decimal | None
    precision: int | None
    allowed_missing_values: str
    codelist: str | None
    data_semantic: str | None
    comments: str | None
    text_max_length: int | None
    text_min_length: int | None
    pattern: str | None
    pattern_err_msg: str | None


@dataclass(frozen=True)
class FieldUiConfigSection:
    control_type: str
    layout: str | None
    text: str | None
    behavior: str | None
    options: dict | None
    style: str | None


@dataclass(frozen=True)
class FieldValidationRuleTranslationSection:
    language_code: str
    message: str


@dataclass(frozen=True)
class FieldValidationRuleSection:
    id: int | None
    rule_type: str
    expression: str
    severity: str
    mode: str
    translations: tuple[FieldValidationRuleTranslationSection, ...]

    @property
    def messages(self):
        return {translation.language_code: translation.message for translation in self.translations}

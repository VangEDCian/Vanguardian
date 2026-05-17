from dataclasses import dataclass

from apps.crf.domain.exceptions import FormBuilderDomainValidationError


@dataclass(frozen=True)
class CrfFieldTemplateEntity:
    field_key: str
    data_type: str
    is_active: bool
    display_order: int
    section_template_id: int | None
    label_en: str
    label_vi: str

    ALLOWED_DATA_TYPES = {
        "BOOLEAN",
        "CODELIST",
        "DATE",
        "DATETIME",
        "DECIMAL",
        "INTEGER",
        "NUMBER",
        "STRING",
        "TEXT",
        "TEXTAREA",
        "TIME",
    }

    @classmethod
    def from_payload(
        cls,
        *,
        field_key,
        data_type,
        is_active,
        display_order,
        section_template_id,
        label_en,
        label_vi,
    ):
        normalized_field_key = (field_key or "").strip()
        if not normalized_field_key:
            raise FormBuilderDomainValidationError("field_key is required.")

        normalized_data_type = cls._normalize_data_type(data_type)
        normalized_display_order = int(display_order or 1)
        if normalized_display_order < 1:
            raise FormBuilderDomainValidationError("display_order must be greater than 0.")

        return cls(
            field_key=normalized_field_key,
            data_type=normalized_data_type,
            is_active=bool(is_active),
            display_order=normalized_display_order,
            section_template_id=section_template_id,
            label_en=(label_en or "").strip(),
            label_vi=(label_vi or "").strip(),
        )

    @classmethod
    def _normalize_data_type(cls, data_type):
        normalized = (data_type or "").strip().upper()
        if not normalized:
            raise FormBuilderDomainValidationError("data_type is required.")
        if normalized not in cls.ALLOWED_DATA_TYPES:
            allowed = ", ".join(sorted(cls.ALLOWED_DATA_TYPES))
            raise FormBuilderDomainValidationError(f"data_type must be one of: {allowed}.")
        return normalized
